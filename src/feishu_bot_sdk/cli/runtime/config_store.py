from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


_CONFIG_VERSION = 1
_DEFAULT_PROFILE = "default"


@dataclass(frozen=True)
class SecretReference:
    backend: str
    key: str

    def to_dict(self) -> dict[str, str]:
        return {"backend": self.backend, "key": self.key}

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> SecretReference | None:
        if not isinstance(value, Mapping):
            return None
        backend = value.get("backend")
        key = value.get("key")
        if not isinstance(backend, str) or not backend:
            return None
        if not isinstance(key, str) or not key:
            return None
        return cls(backend=backend, key=key)


@dataclass(frozen=True)
class CLIProfile:
    name: str
    app_id: str | None = None
    app_secret_ref: SecretReference | None = None
    auth_mode: str | None = None
    base_url: str | None = None
    timeout_seconds: float | None = None
    default_as: str | None = None
    token_store_path: str | None = None
    updated_at: float | None = None

    @property
    def default_identity(self) -> str | None:
        # Backward-compatible alias for legacy runtime/tests while the public
        # product surface converges on `default_as`.
        return self.default_as

    def to_dict(self) -> dict[str, Any]:
        return {
            "app_id": self.app_id,
            "app_secret_ref": self.app_secret_ref.to_dict() if self.app_secret_ref else None,
            "auth_mode": self.auth_mode,
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
            "default_as": self.default_as,
            "default_identity": self.default_as,
            "token_store_path": self.token_store_path,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_mapping(cls, name: str, value: Mapping[str, Any] | None) -> CLIProfile | None:
        if not isinstance(value, Mapping):
            return None
        timeout_seconds = value.get("timeout_seconds")
        normalized_timeout: float | None = None
        if isinstance(timeout_seconds, (int, float)) and not isinstance(timeout_seconds, bool):
            normalized_timeout = float(timeout_seconds)
        elif isinstance(timeout_seconds, str):
            text = timeout_seconds.strip()
            if text:
                try:
                    normalized_timeout = float(text)
                except ValueError:
                    normalized_timeout = None
        updated_at = value.get("updated_at")
        normalized_updated_at: float | None = None
        if isinstance(updated_at, (int, float)) and not isinstance(updated_at, bool):
            normalized_updated_at = float(updated_at)
        return cls(
            name=name,
            app_id=_optional_str(value.get("app_id")),
            app_secret_ref=SecretReference.from_mapping(value.get("app_secret_ref")),
            auth_mode=_optional_str(value.get("auth_mode")),
            base_url=_optional_str(value.get("base_url")),
            timeout_seconds=normalized_timeout,
            default_as=(
                _optional_str(value.get("default_as"))
                or _optional_str(value.get("default_identity"))
            ),
            token_store_path=_optional_str(value.get("token_store_path")),
            updated_at=normalized_updated_at,
        )


@dataclass(frozen=True)
class CLIConfig:
    version: int = _CONFIG_VERSION
    default_profile: str = _DEFAULT_PROFILE
    profiles: dict[str, CLIProfile] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "default_profile": self.default_profile,
            "profiles": {name: profile.to_dict() for name, profile in sorted(self.profiles.items())},
        }

    @classmethod
    def empty(cls) -> CLIConfig:
        return cls(version=_CONFIG_VERSION, default_profile=_DEFAULT_PROFILE, profiles={})

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> CLIConfig:
        if not isinstance(value, Mapping):
            return cls.empty()
        default_profile = _optional_str(value.get("default_profile")) or _DEFAULT_PROFILE
        profiles_raw = value.get("profiles")
        profiles: dict[str, CLIProfile] = {}
        if isinstance(profiles_raw, Mapping):
            for name, item in profiles_raw.items():
                if not isinstance(name, str) or not name:
                    continue
                profile = CLIProfile.from_mapping(name, item if isinstance(item, Mapping) else None)
                if profile is not None:
                    profiles[name] = profile
        version = value.get("version")
        if not isinstance(version, int):
            version = _CONFIG_VERSION
        return cls(version=version, default_profile=default_profile, profiles=profiles)

    def profile(self, name: str) -> CLIProfile | None:
        return self.profiles.get(name)

    def with_profile(self, profile: CLIProfile, *, set_default: bool = False) -> CLIConfig:
        profiles = dict(self.profiles)
        profiles[profile.name] = profile
        default_profile = self.default_profile
        if set_default or not default_profile or default_profile not in profiles:
            default_profile = profile.name
        return CLIConfig(version=_CONFIG_VERSION, default_profile=default_profile, profiles=profiles)

    def without_profile(self, name: str) -> CLIConfig:
        profiles = dict(self.profiles)
        profiles.pop(name, None)
        default_profile = self.default_profile
        if default_profile == name:
            default_profile = sorted(profiles)[0] if profiles else _DEFAULT_PROFILE
        return CLIConfig(version=_CONFIG_VERSION, default_profile=default_profile, profiles=profiles)

    def with_default_profile(self, name: str) -> CLIConfig:
        if name not in self.profiles:
            raise KeyError(name)
        return CLIConfig(version=_CONFIG_VERSION, default_profile=name, profiles=dict(self.profiles))


def default_cli_config_root() -> Path:
    if os.name == "nt":
        appdata = os.getenv("APPDATA")
        if appdata:
            return Path(appdata) / "feishu-bot-sdk"
        return Path.home() / ".feishu-bot-sdk"
    xdg_config_home = os.getenv("XDG_CONFIG_HOME")
    if xdg_config_home:
        return Path(xdg_config_home) / "feishu-bot-sdk"
    return Path.home() / ".config" / "feishu-bot-sdk"


def default_cli_config_path() -> Path:
    override = os.getenv("FEISHU_CLI_CONFIG_PATH")
    if override:
        return Path(override)
    return default_cli_config_root() / "cli-config.json"


def load_cli_config(path: Path | None = None) -> CLIConfig:
    target = path or default_cli_config_path()
    if not target.exists():
        return CLIConfig.empty()
    text = target.read_text(encoding="utf-8").strip()
    if not text:
        return CLIConfig.empty()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return CLIConfig.empty()
    return CLIConfig.from_mapping(parsed if isinstance(parsed, Mapping) else None)


def save_cli_config(config: CLIConfig, path: Path | None = None) -> Path:
    target = path or default_cli_config_path()
    _atomic_write_json(target, config.to_dict())
    return target


def resolve_cli_profile_name(profile: str | None = None, *, config: CLIConfig | None = None) -> str:
    if profile:
        normalized = profile.strip()
        if normalized:
            return normalized
    env_profile = os.getenv("FEISHU_PROFILE")
    if env_profile:
        normalized = env_profile.strip()
        if normalized:
            return normalized
    active_config = config or load_cli_config()
    default_profile = active_config.default_profile.strip() if active_config.default_profile else ""
    if default_profile:
        return default_profile
    return _DEFAULT_PROFILE


def make_profile(
    name: str,
    *,
    app_id: str | None,
    app_secret_ref: SecretReference | None,
    auth_mode: str | None,
    base_url: str | None,
    timeout_seconds: float | None,
    default_as: str | None,
    token_store_path: str | None,
) -> CLIProfile:
    return CLIProfile(
        name=name,
        app_id=_optional_str(app_id),
        app_secret_ref=app_secret_ref,
        auth_mode=_optional_str(auth_mode),
        base_url=_optional_str(base_url),
        timeout_seconds=float(timeout_seconds) if timeout_seconds is not None else None,
        default_as=_optional_str(default_as),
        token_store_path=_optional_str(token_store_path),
        updated_at=time.time(),
    )


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return str(value)


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        _try_chmod(path.parent, 0o700)
    serialized = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f"{path.name}.",
        suffix=".tmp",
        dir=str(path.parent) if path.parent else None,
        text=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(serialized)
        os.replace(tmp_name, path)
        _try_chmod(path, 0o600)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def _try_chmod(path: Path, mode: int) -> None:
    if os.name == "nt":
        return
    try:
        os.chmod(path, mode)
    except OSError:
        return


__all__ = [
    "CLIConfig",
    "CLIProfile",
    "SecretReference",
    "default_cli_config_path",
    "default_cli_config_root",
    "load_cli_config",
    "make_profile",
    "resolve_cli_profile_name",
    "save_cli_config",
]
