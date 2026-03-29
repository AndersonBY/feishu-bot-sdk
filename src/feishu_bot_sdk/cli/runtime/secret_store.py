from __future__ import annotations

import base64
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

from Crypto.Cipher import AES

from .config_store import SecretReference, default_cli_config_root


_SECRET_STORE_VERSION = 1
_SECRET_BACKEND = "encrypted_file"


class EncryptedFileSecretStore:
    backend_name = _SECRET_BACKEND

    def __init__(self, *, store_path: Path, key_path: Path) -> None:
        self._store_path = store_path
        self._key_path = key_path

    @property
    def store_path(self) -> Path:
        return self._store_path

    @property
    def key_path(self) -> Path:
        return self._key_path

    def put(self, key: str, secret: str) -> SecretReference:
        normalized_key = _normalize_key(key)
        if not secret:
            raise ValueError("secret value cannot be empty")
        master_key = self._load_or_create_master_key()
        nonce = os.urandom(12)
        cipher = AES.new(master_key, AES.MODE_GCM, nonce=nonce)
        ciphertext, tag = cipher.encrypt_and_digest(secret.encode("utf-8"))

        payload = self._read_store()
        secrets = payload.get("secrets")
        if not isinstance(secrets, dict):
            secrets = {}
        secrets[normalized_key] = {
            "nonce": _b64encode(nonce),
            "ciphertext": _b64encode(ciphertext),
            "tag": _b64encode(tag),
        }
        payload["version"] = _SECRET_STORE_VERSION
        payload["secrets"] = secrets
        _atomic_write_json(self._store_path, payload)
        return SecretReference(backend=self.backend_name, key=normalized_key)

    def get(self, reference: SecretReference | str) -> str | None:
        normalized_key = self._resolve_reference(reference)
        payload = self._read_store()
        secrets = payload.get("secrets")
        if not isinstance(secrets, Mapping):
            return None
        item = secrets.get(normalized_key)
        if not isinstance(item, Mapping):
            return None
        nonce = _b64decode(item.get("nonce"))
        ciphertext = _b64decode(item.get("ciphertext"))
        tag = _b64decode(item.get("tag"))
        if nonce is None or ciphertext is None or tag is None:
            return None
        master_key = self._load_or_create_master_key()
        cipher = AES.new(master_key, AES.MODE_GCM, nonce=nonce)
        try:
            plaintext = cipher.decrypt_and_verify(ciphertext, tag)
        except ValueError:
            return None
        return plaintext.decode("utf-8")

    def delete(self, reference: SecretReference | str) -> bool:
        normalized_key = self._resolve_reference(reference)
        payload = self._read_store()
        secrets = payload.get("secrets")
        if not isinstance(secrets, dict):
            return False
        if normalized_key not in secrets:
            return False
        del secrets[normalized_key]
        payload["version"] = _SECRET_STORE_VERSION
        payload["secrets"] = secrets
        _atomic_write_json(self._store_path, payload)
        return True

    def _resolve_reference(self, reference: SecretReference | str) -> str:
        if isinstance(reference, SecretReference):
            if reference.backend != self.backend_name:
                raise ValueError(
                    f"unsupported secret backend {reference.backend!r}, expected {self.backend_name!r}"
                )
            return _normalize_key(reference.key)
        return _normalize_key(reference)

    def _read_store(self) -> dict[str, Any]:
        if not self._store_path.exists():
            return {"version": _SECRET_STORE_VERSION, "secrets": {}}
        text = self._store_path.read_text(encoding="utf-8").strip()
        if not text:
            return {"version": _SECRET_STORE_VERSION, "secrets": {}}
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {"version": _SECRET_STORE_VERSION, "secrets": {}}
        if not isinstance(parsed, dict):
            return {"version": _SECRET_STORE_VERSION, "secrets": {}}
        return parsed

    def _load_or_create_master_key(self) -> bytes:
        if self._key_path.exists():
            data = self._key_path.read_bytes()
            if len(data) == 32:
                return data
        if self._key_path.parent and not self._key_path.parent.exists():
            self._key_path.parent.mkdir(parents=True, exist_ok=True)
            _try_chmod(self._key_path.parent, 0o700)
        key = os.urandom(32)
        fd, tmp_name = tempfile.mkstemp(
            prefix=f"{self._key_path.name}.",
            suffix=".tmp",
            dir=str(self._key_path.parent) if self._key_path.parent else None,
        )
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(key)
            os.replace(tmp_name, self._key_path)
            _try_chmod(self._key_path, 0o600)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
        return key


def default_secret_store_path() -> Path:
    override = os.getenv("FEISHU_SECRET_STORE_PATH")
    if override:
        return Path(override)
    return default_cli_config_root() / "cli-secrets.json"


def default_secret_key_path() -> Path:
    override = os.getenv("FEISHU_SECRET_STORE_KEY_PATH")
    if override:
        return Path(override)
    return default_cli_config_root() / "cli-secrets.key"


def resolve_secret_store() -> EncryptedFileSecretStore:
    backend = os.getenv("FEISHU_SECRET_STORE_BACKEND", _SECRET_BACKEND).strip().lower() or _SECRET_BACKEND
    if backend != _SECRET_BACKEND:
        raise ValueError(f"unsupported FEISHU_SECRET_STORE_BACKEND {backend!r}")
    return EncryptedFileSecretStore(
        store_path=default_secret_store_path(),
        key_path=default_secret_key_path(),
    )


def _normalize_key(value: str) -> str:
    key = value.strip()
    if not key:
        raise ValueError("secret key cannot be empty")
    return key


def _b64encode(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _b64decode(value: Any) -> bytes | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return base64.b64decode(value.encode("ascii"), validate=True)
    except (ValueError, UnicodeEncodeError):
        return None


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
    "EncryptedFileSecretStore",
    "default_secret_key_path",
    "default_secret_store_path",
    "resolve_secret_store",
]
