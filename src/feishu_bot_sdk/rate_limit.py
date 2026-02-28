import asyncio
import threading
import time
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, Optional


@dataclass(frozen=True)
class RateLimitTuning:
    base_qps: float = 5.0
    min_qps: float = 1.0
    max_qps: float = 50.0
    increase_factor: float = 1.05
    decrease_factor: float = 0.5
    cooldown_seconds: float = 1.0
    max_wait_seconds: float = 30.0


@dataclass
class _BucketState:
    rate: float
    tokens: float
    last_refill: float
    cooldown_until: float = 0.0


def build_rate_limit_key(method: str, path: str) -> str:
    return f"{method.upper()}:{path}"


class AdaptiveRateLimiter:
    def __init__(
        self,
        tuning: Optional[RateLimitTuning] = None,
        *,
        clock: Optional[Callable[[], float]] = None,
        sleeper: Optional[Callable[[float], None]] = None,
    ) -> None:
        self._tuning = tuning or RateLimitTuning()
        self._clock = clock or time.monotonic
        self._sleep = sleeper or time.sleep
        self._states: Dict[str, _BucketState] = {}
        self._lock = threading.Lock()

    def acquire(self, key: str) -> None:
        while True:
            wait_seconds = 0.0
            with self._lock:
                now = self._clock()
                state = self._state(key, now)
                self._refill(state, now)
                if now < state.cooldown_until:
                    wait_seconds = state.cooldown_until - now
                elif state.tokens >= 1.0:
                    state.tokens -= 1.0
                    return
                else:
                    wait_seconds = (1.0 - state.tokens) / max(state.rate, self._tuning.min_qps)
            self._sleep(min(max(wait_seconds, 0.0), self._tuning.max_wait_seconds))

    def on_success(self, key: str) -> None:
        with self._lock:
            now = self._clock()
            state = self._state(key, now)
            self._refill(state, now)
            state.rate = min(self._tuning.max_qps, state.rate * self._tuning.increase_factor)
            state.tokens = min(state.tokens + 0.5, state.rate)

    def on_throttled(self, key: str, retry_after: Optional[float] = None) -> None:
        with self._lock:
            now = self._clock()
            state = self._state(key, now)
            self._refill(state, now)
            state.rate = max(self._tuning.min_qps, state.rate * self._tuning.decrease_factor)
            cool_down = retry_after if retry_after is not None and retry_after > 0 else self._tuning.cooldown_seconds
            state.cooldown_until = max(state.cooldown_until, now + cool_down)
            state.tokens = min(state.tokens, 0.0)

    def _state(self, key: str, now: float) -> _BucketState:
        existing = self._states.get(key)
        if existing is not None:
            return existing
        base_rate = min(max(self._tuning.base_qps, self._tuning.min_qps), self._tuning.max_qps)
        created = _BucketState(rate=base_rate, tokens=base_rate, last_refill=now)
        self._states[key] = created
        return created

    def _refill(self, state: _BucketState, now: float) -> None:
        elapsed = now - state.last_refill
        if elapsed <= 0:
            return
        state.tokens = min(state.rate, state.tokens + elapsed * state.rate)
        state.last_refill = now


class AsyncAdaptiveRateLimiter:
    def __init__(
        self,
        tuning: Optional[RateLimitTuning] = None,
        *,
        clock: Optional[Callable[[], float]] = None,
        sleeper: Optional[Callable[[float], Awaitable[None]]] = None,
    ) -> None:
        self._tuning = tuning or RateLimitTuning()
        self._clock = clock or time.monotonic
        self._sleep = sleeper or asyncio.sleep
        self._states: Dict[str, _BucketState] = {}
        self._lock = asyncio.Lock()

    async def acquire(self, key: str) -> None:
        while True:
            wait_seconds = 0.0
            async with self._lock:
                now = self._clock()
                state = self._state(key, now)
                self._refill(state, now)
                if now < state.cooldown_until:
                    wait_seconds = state.cooldown_until - now
                elif state.tokens >= 1.0:
                    state.tokens -= 1.0
                    return
                else:
                    wait_seconds = (1.0 - state.tokens) / max(state.rate, self._tuning.min_qps)
            await self._sleep(min(max(wait_seconds, 0.0), self._tuning.max_wait_seconds))

    async def on_success(self, key: str) -> None:
        async with self._lock:
            now = self._clock()
            state = self._state(key, now)
            self._refill(state, now)
            state.rate = min(self._tuning.max_qps, state.rate * self._tuning.increase_factor)
            state.tokens = min(state.tokens + 0.5, state.rate)

    async def on_throttled(self, key: str, retry_after: Optional[float] = None) -> None:
        async with self._lock:
            now = self._clock()
            state = self._state(key, now)
            self._refill(state, now)
            state.rate = max(self._tuning.min_qps, state.rate * self._tuning.decrease_factor)
            cool_down = retry_after if retry_after is not None and retry_after > 0 else self._tuning.cooldown_seconds
            state.cooldown_until = max(state.cooldown_until, now + cool_down)
            state.tokens = min(state.tokens, 0.0)

    def _state(self, key: str, now: float) -> _BucketState:
        existing = self._states.get(key)
        if existing is not None:
            return existing
        base_rate = min(max(self._tuning.base_qps, self._tuning.min_qps), self._tuning.max_qps)
        created = _BucketState(rate=base_rate, tokens=base_rate, last_refill=now)
        self._states[key] = created
        return created

    def _refill(self, state: _BucketState, now: float) -> None:
        elapsed = now - state.last_refill
        if elapsed <= 0:
            return
        state.tokens = min(state.rate, state.tokens + elapsed * state.rate)
        state.last_refill = now
