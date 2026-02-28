import asyncio
import threading
import time
from typing import Dict, Optional

from .types import EventEnvelope


def build_idempotency_key(envelope: EventEnvelope) -> Optional[str]:
    if envelope.is_url_verification:
        return None
    if envelope.event_id:
        return envelope.event_id
    return None


class MemoryIdempotencyStore:
    def __init__(self, *, cleanup_interval_seconds: float = 300.0) -> None:
        self._cleanup_interval_seconds = cleanup_interval_seconds
        self._data: Dict[str, float] = {}
        self._last_cleanup = 0.0
        self._lock = threading.Lock()

    def mark_once(self, key: str, *, ttl_seconds: float = 86_400.0) -> bool:
        if not key:
            return True
        now = time.monotonic()
        with self._lock:
            self._cleanup_if_needed(now)
            expires_at = self._data.get(key)
            if expires_at is not None and expires_at > now:
                return False
            self._data[key] = now + ttl_seconds
            return True

    def seen(self, key: str) -> bool:
        if not key:
            return False
        now = time.monotonic()
        with self._lock:
            self._cleanup_if_needed(now)
            expires_at = self._data.get(key)
            return expires_at is not None and expires_at > now

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def _cleanup_if_needed(self, now: float) -> None:
        if now - self._last_cleanup < self._cleanup_interval_seconds:
            return
        self._last_cleanup = now
        expired_keys = [key for key, expires_at in self._data.items() if expires_at <= now]
        for key in expired_keys:
            self._data.pop(key, None)


class AsyncMemoryIdempotencyStore:
    def __init__(self, *, cleanup_interval_seconds: float = 300.0) -> None:
        self._cleanup_interval_seconds = cleanup_interval_seconds
        self._data: Dict[str, float] = {}
        self._last_cleanup = 0.0
        self._lock = asyncio.Lock()

    async def mark_once(self, key: str, *, ttl_seconds: float = 86_400.0) -> bool:
        if not key:
            return True
        now = time.monotonic()
        async with self._lock:
            self._cleanup_if_needed(now)
            expires_at = self._data.get(key)
            if expires_at is not None and expires_at > now:
                return False
            self._data[key] = now + ttl_seconds
            return True

    async def seen(self, key: str) -> bool:
        if not key:
            return False
        now = time.monotonic()
        async with self._lock:
            self._cleanup_if_needed(now)
            expires_at = self._data.get(key)
            return expires_at is not None and expires_at > now

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._data.pop(key, None)

    async def clear(self) -> None:
        async with self._lock:
            self._data.clear()

    def _cleanup_if_needed(self, now: float) -> None:
        if now - self._last_cleanup < self._cleanup_interval_seconds:
            return
        self._last_cleanup = now
        expired_keys = [key for key, expires_at in self._data.items() if expires_at <= now]
        for key in expired_keys:
            self._data.pop(key, None)
