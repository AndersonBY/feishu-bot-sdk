import asyncio
from typing import Any, Mapping, Optional, cast

import pytest

from feishu_bot_sdk.config import FeishuConfig
from feishu_bot_sdk.exceptions import HTTPRequestError
from feishu_bot_sdk.feishu import AsyncFeishuClient, FeishuClient
from feishu_bot_sdk.http_client import AsyncJsonHttpClient, JsonHttpClient
from feishu_bot_sdk.rate_limit import AdaptiveRateLimiter, AsyncAdaptiveRateLimiter, RateLimitTuning


class _LimiterStub:
    def __init__(self) -> None:
        self.acquired: list[str] = []
        self.successes: list[str] = []
        self.throttled: list[tuple[str, Optional[float]]] = []

    def acquire(self, key: str) -> None:
        self.acquired.append(key)

    def on_success(self, key: str) -> None:
        self.successes.append(key)

    def on_throttled(self, key: str, retry_after: Optional[float] = None) -> None:
        self.throttled.append((key, retry_after))


class _AsyncLimiterStub:
    def __init__(self) -> None:
        self.acquired: list[str] = []
        self.successes: list[str] = []
        self.throttled: list[tuple[str, Optional[float]]] = []

    async def acquire(self, key: str) -> None:
        self.acquired.append(key)

    async def on_success(self, key: str) -> None:
        self.successes.append(key)

    async def on_throttled(self, key: str, retry_after: Optional[float] = None) -> None:
        self.throttled.append((key, retry_after))


class _SyncHttpStub:
    def __init__(self, resolver: Any) -> None:
        self._resolver = resolver

    def request_json(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        params: Optional[Mapping[str, object]] = None,
        payload: Optional[Mapping[str, object]] = None,
        timeout_seconds: Optional[float] = None,
    ) -> Mapping[str, Any]:
        return self._resolver(
            {
                "method": method,
                "url": url,
                "headers": dict(headers or {}),
                "params": dict(params or {}),
                "payload": dict(payload or {}),
                "timeout": timeout_seconds,
            }
        )


class _AsyncHttpStub:
    def __init__(self, resolver: Any) -> None:
        self._resolver = resolver

    async def request_json(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        params: Optional[Mapping[str, object]] = None,
        payload: Optional[Mapping[str, object]] = None,
        timeout_seconds: Optional[float] = None,
    ) -> Mapping[str, Any]:
        return self._resolver(
            {
                "method": method,
                "url": url,
                "headers": dict(headers or {}),
                "params": dict(params or {}),
                "payload": dict(payload or {}),
                "timeout": timeout_seconds,
            }
        )

    async def aclose(self) -> None:
        return None


def test_adaptive_rate_limiter_waits_after_throttle():
    now = [0.0]
    waits: list[float] = []

    def clock() -> float:
        return now[0]

    def sleeper(seconds: float) -> None:
        waits.append(seconds)
        now[0] += seconds

    limiter = AdaptiveRateLimiter(
        RateLimitTuning(base_qps=2.0, min_qps=1.0, cooldown_seconds=1.0),
        clock=clock,
        sleeper=sleeper,
    )

    limiter.acquire("GET:/bitable/v1/apps")
    limiter.on_throttled("GET:/bitable/v1/apps", retry_after=2.0)
    limiter.acquire("GET:/bitable/v1/apps")

    assert waits == [2.0]


def test_feishu_client_calls_rate_limiter_hooks():
    limiter = _LimiterStub()
    http = _SyncHttpStub(lambda _call: {"code": 0, "data": {"ok": True}})
    client = FeishuClient(
        FeishuConfig(
            app_id="cli_1",
            app_secret="secret_1",
            access_token="t-1",
            rate_limit_enabled=False,
        ),
        http_client=cast(JsonHttpClient, http),
        rate_limiter=cast(AdaptiveRateLimiter, limiter),
    )

    data = client.request_json("GET", "/im/v1/messages", params={"page_size": 20})

    assert data == {"code": 0, "data": {"ok": True}}
    assert limiter.acquired == ["GET:/im/v1/messages"]
    assert limiter.successes == ["GET:/im/v1/messages"]
    assert limiter.throttled == []


def test_feishu_client_throttles_on_http_429():
    limiter = _LimiterStub()

    def resolver(_call: Mapping[str, Any]) -> Mapping[str, Any]:
        raise HTTPRequestError(
            "too many requests",
            status_code=429,
            response_headers={"Retry-After": "3"},
        )

    http = _SyncHttpStub(resolver)
    client = FeishuClient(
        FeishuConfig(
            app_id="cli_1",
            app_secret="secret_1",
            access_token="t-1",
            rate_limit_enabled=False,
        ),
        http_client=cast(JsonHttpClient, http),
        rate_limiter=cast(AdaptiveRateLimiter, limiter),
    )

    with pytest.raises(HTTPRequestError):
        client.request_json("POST", "/im/v1/messages", payload={"receive_id": "ou_1"})

    assert limiter.acquired == ["POST:/im/v1/messages"]
    assert limiter.successes == []
    assert limiter.throttled == [("POST:/im/v1/messages", 3.0)]


def test_async_feishu_client_calls_rate_limiter_hooks():
    async def run() -> None:
        limiter = _AsyncLimiterStub()
        http = _AsyncHttpStub(lambda _call: {"code": 0, "data": {"ok": True}})
        client = AsyncFeishuClient(
            FeishuConfig(
                app_id="cli_1",
                app_secret="secret_1",
                access_token="t-1",
                rate_limit_enabled=False,
            ),
            http_client=cast(AsyncJsonHttpClient, http),
            rate_limiter=cast(AsyncAdaptiveRateLimiter, limiter),
        )
        data = await client.request_json("GET", "/wiki/v2/spaces", params={"page_size": 10})
        assert data == {"code": 0, "data": {"ok": True}}
        assert limiter.acquired == ["GET:/wiki/v2/spaces"]
        assert limiter.successes == ["GET:/wiki/v2/spaces"]
        assert limiter.throttled == []

    asyncio.run(run())


def test_async_adaptive_rate_limiter_waits_after_throttle():
    now = [0.0]
    waits: list[float] = []

    def clock() -> float:
        return now[0]

    async def sleeper(seconds: float) -> None:
        waits.append(seconds)
        now[0] += seconds

    limiter = AsyncAdaptiveRateLimiter(
        RateLimitTuning(base_qps=2.0, min_qps=1.0, cooldown_seconds=1.0),
        clock=clock,
        sleeper=sleeper,
    )

    async def run() -> None:
        await limiter.acquire("GET:/wiki/v2/spaces")
        await limiter.on_throttled("GET:/wiki/v2/spaces", retry_after=1.5)
        await limiter.acquire("GET:/wiki/v2/spaces")

    asyncio.run(run())
    assert waits == [1.5]
