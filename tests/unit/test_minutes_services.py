import asyncio
from typing import Any, Mapping, Optional, cast

from feishu_bot_sdk.feishu import AsyncFeishuClient, FeishuClient
from feishu_bot_sdk.minutes import AsyncMinutesService, MinutesService


class _SyncClientStub:
    def __init__(self, resolver: Any) -> None:
        self._resolver = resolver
        self.calls: list[dict[str, Any]] = []

    def request_json(
        self,
        method: str,
        path: str,
        *,
        payload: Optional[Mapping[str, object]] = None,
        params: Optional[Mapping[str, object]] = None,
    ) -> Mapping[str, Any]:
        call = {
            "method": method,
            "path": path,
            "payload": dict(payload or {}),
            "params": dict(params or {}),
        }
        self.calls.append(call)
        return self._resolver(call)


class _AsyncClientStub:
    def __init__(self, resolver: Any) -> None:
        self._resolver = resolver
        self.calls: list[dict[str, Any]] = []

    async def request_json(
        self,
        method: str,
        path: str,
        *,
        payload: Optional[Mapping[str, object]] = None,
        params: Optional[Mapping[str, object]] = None,
    ) -> Mapping[str, Any]:
        call = {
            "method": method,
            "path": path,
            "payload": dict(payload or {}),
            "params": dict(params or {}),
        }
        self.calls.append(call)
        return self._resolver(call)


def test_minutes_service_request_shapes() -> None:
    stub = _SyncClientStub(lambda _call: {"code": 0, "data": {"ok": True}})
    service = MinutesService(cast(FeishuClient, stub))

    service.get_minute("min_1", user_id_type="open_id")
    service.get_minute_media_download_url("min_1")

    assert stub.calls == [
        {
            "method": "GET",
            "path": "/minutes/v1/minutes/min_1",
            "payload": {},
            "params": {"user_id_type": "open_id"},
        },
        {
            "method": "GET",
            "path": "/minutes/v1/minutes/min_1/media",
            "payload": {},
            "params": {},
        },
    ]


def test_async_minutes_service_request_shapes() -> None:
    stub = _AsyncClientStub(lambda _call: {"code": 0, "data": {"ok": True}})
    service = AsyncMinutesService(cast(AsyncFeishuClient, stub))

    async def run() -> None:
        await service.get_minute("min_1", user_id_type="open_id")
        await service.get_minute_media_download_url("min_1")

    asyncio.run(run())

    assert stub.calls == [
        {
            "method": "GET",
            "path": "/minutes/v1/minutes/min_1",
            "payload": {},
            "params": {"user_id_type": "open_id"},
        },
        {
            "method": "GET",
            "path": "/minutes/v1/minutes/min_1/media",
            "payload": {},
            "params": {},
        },
    ]
