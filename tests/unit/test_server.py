import asyncio
from typing import Any

import pytest

from feishu_bot_sdk.events import build_event_context
from feishu_bot_sdk.server import FeishuBotServer


class _BlockingWSClient:
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.stopped = asyncio.Event()
        self._release = asyncio.Event()

    async def start(self) -> None:
        self.started.set()
        await self._release.wait()

    async def stop(self) -> None:
        self.stopped.set()
        self._release.set()


class _ErrorWSClient:
    async def start(self) -> None:
        raise RuntimeError("boom")

    async def stop(self) -> None:
        return None


def test_server_start_stop_lifecycle():
    async def run() -> None:
        fake_client = _BlockingWSClient()
        server = FeishuBotServer(
            app_id="cli_test",
            app_secret="secret_test",
            ws_client_factory=lambda _registry: fake_client,
        )
        await server.start()
        await asyncio.wait_for(fake_client.started.wait(), timeout=1)

        status_running = server.status()
        assert status_running.running is True
        assert status_running.started_at is not None

        await server.stop()
        status_stopped = server.status()
        assert status_stopped.running is False
        assert status_stopped.stopped_at is not None
        assert fake_client.stopped.is_set() is True

    asyncio.run(run())


def test_server_on_event_and_default_updates_stats():
    server = FeishuBotServer(
        app_id="cli_test",
        app_secret="secret_test",
        ws_client_factory=lambda _registry: _BlockingWSClient(),
    )

    captured: list[str] = []
    server.on_event("im.message.receive_v1", lambda ctx: captured.append(ctx.envelope.event_type))

    message_payload = {
        "schema": "2.0",
        "header": {"event_id": "evt_1", "event_type": "im.message.receive_v1"},
        "event": {"message": {"message_id": "om_1", "content": "{\"text\":\"hello\"}"}},
    }
    server.registry.dispatch(build_event_context(message_payload))
    assert captured == ["im.message.receive_v1"]

    default_captured: list[str] = []
    server.on_default(lambda ctx: default_captured.append(ctx.envelope.event_type))
    default_payload = {
        "schema": "2.0",
        "header": {"event_id": "evt_2", "event_type": "application.bot.menu_v6"},
        "event": {},
    }
    server.registry.dispatch(build_event_context(default_payload))
    assert default_captured == ["application.bot.menu_v6"]

    status = server.status()
    assert status.total_events == 2
    assert status.event_counts["im.message.receive_v1"] == 1
    assert status.event_counts["application.bot.menu_v6"] == 1
    assert status.last_event_type == "application.bot.menu_v6"


def test_server_typed_handler_registration():
    server = FeishuBotServer(
        app_id="cli_test",
        app_secret="secret_test",
        ws_client_factory=lambda _registry: _BlockingWSClient(),
    )
    open_ids: list[str] = []
    server.on_im_message_receive(lambda event: open_ids.append(event.sender_open_id or ""))

    payload = {
        "schema": "2.0",
        "header": {"event_id": "evt_3", "event_type": "im.message.receive_v1"},
        "event": {
            "message": {
                "message_id": "om_1",
                "message_type": "text",
                "content": "{\"text\":\"hello\"}",
            },
            "sender": {
                "sender_id": {
                    "open_id": "ou_test",
                }
            },
        },
    }
    server.registry.dispatch(build_event_context(payload))
    assert open_ids == ["ou_test"]
    assert server.status().event_counts["im.message.receive_v1"] == 1


def test_run_forever_propagates_client_error():
    async def run() -> None:
        server = FeishuBotServer(
            app_id="cli_test",
            app_secret="secret_test",
            ws_client_factory=lambda _registry: _ErrorWSClient(),
        )
        with pytest.raises(RuntimeError, match="boom"):
            await server.run_forever(handle_signals=False)
        status = server.status()
        assert status.running is False
        assert status.last_error is not None
        assert "RuntimeError: boom" in status.last_error

    asyncio.run(run())


def test_on_default_supports_async_handler():
    async def run() -> None:
        server = FeishuBotServer(
            app_id="cli_test",
            app_secret="secret_test",
            ws_client_factory=lambda _registry: _BlockingWSClient(),
        )
        captured: list[str] = []

        async def handler(ctx: Any) -> None:
            captured.append(ctx.envelope.event_type)

        server.on_default(handler)
        payload = {
            "schema": "2.0",
            "header": {"event_id": "evt_4", "event_type": "custom.event"},
            "event": {},
        }
        await server.registry.adispatch(build_event_context(payload))

        assert captured == ["custom.event"]
        assert server.status().event_counts["custom.event"] == 1

    asyncio.run(run())

