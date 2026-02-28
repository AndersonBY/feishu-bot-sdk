import hashlib
import hmac
import time
from typing import Mapping, Optional

from .errors import WebhookSignatureError, WebhookTimestampError

_HEADER_TIMESTAMP = "x-lark-request-timestamp"
_HEADER_NONCE = "x-lark-request-nonce"
_HEADER_SIGNATURE = "x-lark-signature"


def _get_header(headers: Mapping[str, str], key: str) -> Optional[str]:
    key_lower = key.lower()
    for name, value in headers.items():
        if name.lower() == key_lower:
            return value
    return None


def verify_timestamp(
    timestamp: str,
    *,
    tolerance_seconds: float = 300.0,
    now: Optional[float] = None,
) -> None:
    if not timestamp:
        raise WebhookTimestampError("missing timestamp header")
    try:
        timestamp_value = float(timestamp)
    except ValueError as exc:
        raise WebhookTimestampError("invalid timestamp header") from exc
    if timestamp_value > 1_000_000_000_000:
        timestamp_value = timestamp_value / 1000.0
    now_value = now if now is not None else time.time()
    if abs(now_value - timestamp_value) > tolerance_seconds:
        raise WebhookTimestampError("timestamp is outside allowed range")


def compute_signature(
    timestamp: str,
    nonce: str,
    encrypt_key: str,
    raw_body: bytes,
) -> str:
    message = (timestamp + nonce + encrypt_key).encode("utf-8") + raw_body
    digest = hashlib.sha256(message)
    return digest.hexdigest()


def verify_signature(
    headers: Mapping[str, str],
    raw_body: bytes,
    *,
    encrypt_key: str,
    tolerance_seconds: float = 300.0,
    now: Optional[float] = None,
) -> None:
    if not encrypt_key:
        return
    timestamp = _get_header(headers, _HEADER_TIMESTAMP)
    nonce = _get_header(headers, _HEADER_NONCE)
    signature = _get_header(headers, _HEADER_SIGNATURE)
    if not timestamp or not nonce or not signature:
        raise WebhookSignatureError("missing signature headers")
    verify_timestamp(timestamp, tolerance_seconds=tolerance_seconds, now=now)
    expected = compute_signature(timestamp, nonce, encrypt_key, raw_body)
    if not hmac.compare_digest(expected, signature):
        raise WebhookSignatureError("signature verification failed")
