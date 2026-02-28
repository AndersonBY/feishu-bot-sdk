import base64
import hashlib
import json
from typing import Any, Dict, Mapping, Optional

from .errors import WebhookDecryptError

try:
    from Crypto.Cipher import AES
except ImportError:  # pragma: no cover
    AES = None  # type: ignore[assignment]


def decode_webhook_body(
    raw_body: bytes,
    *,
    encrypt_key: Optional[str] = None,
) -> Dict[str, Any]:
    payload = _load_json(raw_body)
    encrypt_value = payload.get("encrypt")
    if isinstance(encrypt_value, str) and encrypt_value:
        if not encrypt_key:
            raise WebhookDecryptError("encrypt_key is required for encrypted webhook payload")
        return decrypt_event_payload(encrypt_value, encrypt_key)
    return payload


def decrypt_event_payload(encrypt: str, encrypt_key: str) -> Dict[str, Any]:
    if AES is None:
        raise WebhookDecryptError("pycryptodome is required for encrypted webhook payload")
    key = hashlib.sha256(encrypt_key.encode("utf-8")).digest()
    try:
        encrypted_bytes = base64.b64decode(encrypt)
    except ValueError as exc:
        raise WebhookDecryptError("invalid encrypted payload") from exc
    if len(encrypted_bytes) < AES.block_size:
        raise WebhookDecryptError("encrypted payload too short")
    iv = encrypted_bytes[: AES.block_size]
    ciphertext = encrypted_bytes[AES.block_size :]
    if len(ciphertext) % AES.block_size != 0:
        raise WebhookDecryptError("invalid encrypted payload block size")
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded = cipher.decrypt(ciphertext)
    plaintext_bytes = _pkcs7_unpad(padded)
    return _load_json(plaintext_bytes)


def _pkcs7_unpad(data: bytes) -> bytes:
    if not data:
        raise WebhookDecryptError("empty decrypted payload")
    padding_size = data[-1]
    if padding_size < 1 or padding_size > 16:
        raise WebhookDecryptError("invalid decrypted payload padding")
    if data[-padding_size:] != bytes([padding_size]) * padding_size:
        raise WebhookDecryptError("invalid decrypted payload padding")
    return data[:-padding_size]


def _load_json(raw: bytes) -> Dict[str, Any]:
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WebhookDecryptError("webhook body is not valid json") from exc
    if not isinstance(data, Mapping):
        raise WebhookDecryptError("webhook body must be a json object")
    return {str(k): v for k, v in data.items()}
