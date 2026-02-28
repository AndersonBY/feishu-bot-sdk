import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import betterproto2

from .constants import FRAME_TYPE_CONTROL, HEADER_TYPE, MESSAGE_TYPE_PING


@dataclass(eq=False, repr=False)
class Header(betterproto2.Message):
    key: str = betterproto2.field(1, betterproto2.TYPE_STRING)
    value: str = betterproto2.field(2, betterproto2.TYPE_STRING)


@dataclass(eq=False, repr=False)
class Frame(betterproto2.Message):
    SeqID: int = betterproto2.field(1, betterproto2.TYPE_UINT64)
    LogID: int = betterproto2.field(2, betterproto2.TYPE_UINT64)
    service: int = betterproto2.field(3, betterproto2.TYPE_INT32)
    method: int = betterproto2.field(4, betterproto2.TYPE_INT32)
    headers: list[Header] = betterproto2.field(5, betterproto2.TYPE_MESSAGE, repeated=True)
    payload_encoding: str = betterproto2.field(6, betterproto2.TYPE_STRING)
    payload_type: str = betterproto2.field(7, betterproto2.TYPE_STRING)
    payload: bytes = betterproto2.field(8, betterproto2.TYPE_BYTES)
    LogIDNew: str = betterproto2.field(9, betterproto2.TYPE_STRING)


def new_ping_frame(service_id: int):
    frame = Frame()
    frame.service = service_id
    frame.method = FRAME_TYPE_CONTROL
    frame.SeqID = 0
    frame.LogID = int(time.time() * 1000)
    frame.headers.append(Header(key=HEADER_TYPE, value=MESSAGE_TYPE_PING))
    return frame


def parse_frame(raw_message: bytes):
    frame = Frame()
    return frame.parse(raw_message)


def serialize_frame(frame: Any) -> bytes:
    return frame.SerializeToString()


def frame_headers_to_dict(frame: Any) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for item in frame.headers:
        result[item.key] = item.value
    return result


def add_frame_header(frame: Any, key: str, value: str) -> None:
    frame.headers.append(Header(key=key, value=value))


@dataclass
class _Fragment:
    expires_at: float
    chunks: Dict[int, bytes]
    total: int


class FrameCombiner:
    def __init__(self, *, ttl_seconds: float = 5.0) -> None:
        self._ttl_seconds = ttl_seconds
        self._fragments: Dict[str, _Fragment] = {}

    def append(
        self,
        message_id: str,
        payload: bytes,
        *,
        total: int,
        seq: int,
        now: Optional[float] = None,
    ) -> Optional[bytes]:
        now_value = now or time.monotonic()
        self._cleanup(now_value)
        fragment = self._fragments.get(message_id)
        if fragment is None:
            fragment = _Fragment(
                expires_at=now_value + self._ttl_seconds,
                chunks={},
                total=total,
            )
            self._fragments[message_id] = fragment
        fragment.chunks[seq] = payload
        fragment.expires_at = now_value + self._ttl_seconds
        if len(fragment.chunks) < fragment.total:
            return None
        merged = b"".join(fragment.chunks.get(index, b"") for index in range(fragment.total))
        if not merged:
            return None
        self._fragments.pop(message_id, None)
        return merged

    def _cleanup(self, now: float) -> None:
        expired = [
            key
            for key, fragment in self._fragments.items()
            if fragment.expires_at <= now
        ]
        for key in expired:
            self._fragments.pop(key, None)
