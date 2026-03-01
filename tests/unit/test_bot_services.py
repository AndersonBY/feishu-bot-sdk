import asyncio
from typing import Any, Mapping, Optional, cast

from feishu_bot_sdk.bot import AsyncBotService, BotService
from feishu_bot_sdk.feishu import AsyncFeishuClient, FeishuClient


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


def test_bot_service_get_info():
    def resolver(_call: Mapping[str, Any]) -> Mapping[str, Any]:
        return {
            "code": 0,
            "msg": "ok",
            "bot": {
                "app_name": "SDK Bot",
                "open_id": "ou_bot_1",
            },
        }

    stub = _SyncClientStub(resolver)
    service = BotService(cast(FeishuClient, stub))
    info = service.get_info()

    assert info == {"app_name": "SDK Bot", "open_id": "ou_bot_1"}
    assert stub.calls == [
        {
            "method": "GET",
            "path": "/bot/v3/info",
            "payload": {},
            "params": {},
        }
    ]


def test_bot_service_get_info_missing_bot_returns_empty():
    def resolver(_call: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"code": 0, "msg": "ok"}

    stub = _SyncClientStub(resolver)
    service = BotService(cast(FeishuClient, stub))

    assert service.get_info() == {}


def test_async_bot_service_get_info():
    def resolver(_call: Mapping[str, Any]) -> Mapping[str, Any]:
        return {
            "code": 0,
            "msg": "ok",
            "bot": {
                "app_name": "Async SDK Bot",
                "open_id": "ou_bot_async",
            },
        }

    stub = _AsyncClientStub(resolver)
    service = AsyncBotService(cast(AsyncFeishuClient, stub))

    async def run() -> None:
        info = await service.get_info()
        assert info == {"app_name": "Async SDK Bot", "open_id": "ou_bot_async"}

    asyncio.run(run())
    assert stub.calls == [
        {
            "method": "GET",
            "path": "/bot/v3/info",
            "payload": {},
            "params": {},
        }
    ]
