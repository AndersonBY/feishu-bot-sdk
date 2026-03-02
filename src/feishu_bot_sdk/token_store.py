from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional


_STORE_VERSION = 1


@dataclass(frozen=True)
class StoredUserToken:
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[float] = None
    refresh_expires_at: Optional[float] = None
    token_type: Optional[str] = None
    scope: Optional[str] = None
    app_id: Optional[str] = None
    tenant_key: Optional[str] = None
    open_id: Optional[str] = None
    user_id: Optional[str] = None
    union_id: Optional[str] = None
    updated_at: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
            "refresh_expires_at": self.refresh_expires_at,
            "token_type": self.token_type,
            "scope": self.scope,
            "app_id": self.app_id,
            "tenant_key": self.tenant_key,
            "open_id": self.open_id,
            "user_id": self.user_id,
            "union_id": self.union_id,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> StoredUserToken | None:
        access_token = value.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            return None
        return cls(
            access_token=access_token,
            refresh_token=_to_optional_str(value.get("refresh_token")),
            expires_at=_to_optional_float(value.get("expires_at")),
            refresh_expires_at=_to_optional_float(value.get("refresh_expires_at")),
            token_type=_to_optional_str(value.get("token_type")),
            scope=_to_optional_str(value.get("scope")),
            app_id=_to_optional_str(value.get("app_id")),
            tenant_key=_to_optional_str(value.get("tenant_key")),
            open_id=_to_optional_str(value.get("open_id")),
            user_id=_to_optional_str(value.get("user_id")),
            union_id=_to_optional_str(value.get("union_id")),
            updated_at=_to_optional_float(value.get("updated_at")),
        )


class TokenStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    def load_profile(self, profile: str) -> StoredUserToken | None:
        data = self._read_store()
        profiles = data.get("profiles")
        if not isinstance(profiles, Mapping):
            return None
        item = profiles.get(profile)
        if not isinstance(item, Mapping):
            return None
        return StoredUserToken.from_mapping(item)

    def save_profile(self, profile: str, token: StoredUserToken) -> None:
        data = self._read_store()
        profiles = data.get("profiles")
        if not isinstance(profiles, dict):
            profiles = {}
        profiles[profile] = token.to_dict()
        data["profiles"] = profiles
        data["version"] = _STORE_VERSION
        self._write_store(data)

    def delete_profile(self, profile: str) -> bool:
        data = self._read_store()
        profiles = data.get("profiles")
        if not isinstance(profiles, dict):
            return False
        if profile not in profiles:
            return False
        del profiles[profile]
        data["profiles"] = profiles
        data["version"] = _STORE_VERSION
        self._write_store(data)
        return True

    def clear(self) -> None:
        self._write_store({"version": _STORE_VERSION, "profiles": {}})

    def _read_store(self) -> dict[str, Any]:
        if not self._path.exists():
            return {"version": _STORE_VERSION, "profiles": {}}
        text = self._path.read_text(encoding="utf-8").strip()
        if not text:
            return {"version": _STORE_VERSION, "profiles": {}}
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {"version": _STORE_VERSION, "profiles": {}}
        if not isinstance(parsed, dict):
            return {"version": _STORE_VERSION, "profiles": {}}
        return parsed

    def _write_store(self, data: Mapping[str, Any]) -> None:
        if self._path.parent and not self._path.parent.exists():
            self._path.parent.mkdir(parents=True, exist_ok=True)
            _try_chmod(self._path.parent, 0o700)
        payload = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
        fd, tmp_name = tempfile.mkstemp(
            prefix=f"{self._path.name}.",
            suffix=".tmp",
            dir=str(self._path.parent) if self._path.parent else None,
            text=True,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                file.write(payload)
            os.replace(tmp_name, self._path)
            _try_chmod(self._path, 0o600)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)


def default_token_store_path() -> Path:
    if os.name == "nt":
        appdata = os.getenv("APPDATA")
        if appdata:
            return Path(appdata) / "feishu-bot-sdk" / "tokens.json"
        return Path.home() / ".feishu-bot-sdk" / "tokens.json"
    return Path.home() / ".config" / "feishu-bot-sdk" / "tokens.json"


def _to_optional_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _to_optional_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None
    return None


def _try_chmod(path: Path, mode: int) -> None:
    if os.name == "nt":
        return
    try:
        os.chmod(path, mode)
    except OSError:
        return
