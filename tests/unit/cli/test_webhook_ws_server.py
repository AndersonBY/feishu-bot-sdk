import asyncio
import json
import time
from pathlib import Path
from typing import Any
from feishu_bot_sdk import cli
from feishu_bot_sdk.events import build_event_context
from feishu_bot_sdk.webhook.security import compute_signature
from feishu_bot_sdk.ws.endpoint import WSEndpoint, WSRemoteConfig


def test_webhook_verify_signature(monkeypatch: Any, capsys: Any) -> None:
    body = '{"schema":"2.0","header":{"event_type":"im.message.receive_v1"}}'
    timestamp = str(int(time.time()))
    nonce = "nonce-1"
    encrypt_key = "encrypt-key-1"
    signature = compute_signature(timestamp, nonce, encrypt_key, body.encode("utf-8"))
    headers = {
        "x-lark-request-timestamp": timestamp,
        "x-lark-request-nonce": nonce,
        "x-lark-signature": signature,
    }

    code = cli.main(
        [
            "webhook",
            "verify-signature",
            "--headers-json",
            json.dumps(headers, ensure_ascii=False),
            "--body-json",
            body,
            "--encrypt-key",
            encrypt_key,
            "--format",
            "json",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True


def test_webhook_parse(monkeypatch: Any, capsys: Any) -> None:
    code = cli.main(
        [
            "webhook",
            "parse",
            "--body-json",
            '{"schema":"2.0","header":{"event_id":"evt_1","event_type":"application.bot.menu_v6"}}',
            "--format",
            "json",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "p2"
    assert payload["event_type"] == "application.bot.menu_v6"
    assert payload["event_id"] == "evt_1"


def test_ws_endpoint(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    def _fake_fetch_ws_endpoint(
        *,
        app_id: str,
        app_secret: str,
        domain: str = "https://open.feishu.cn",
        timeout_seconds: float = 30.0,
    ) -> WSEndpoint:
        assert app_id == "cli_test_app"
        assert app_secret == "cli_test_secret"
        assert domain == "https://open.feishu.cn"
        assert timeout_seconds == 30.0
        return WSEndpoint(
            url="wss://example/ws?device_id=d1&service_id=s1",
            device_id="d1",
            service_id="s1",
            remote_config=WSRemoteConfig(
                reconnect_count=3,
                reconnect_interval_seconds=120.0,
                reconnect_nonce_seconds=30.0,
                ping_interval_seconds=20.0,
            ),
        )

    monkeypatch.setattr(cli, "fetch_ws_endpoint", _fake_fetch_ws_endpoint, raising=False)

    code = cli.main(["ws", "endpoint", "--format", "json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["device_id"] == "d1"
    assert payload["remote_config"]["reconnect_count"] == 3


def test_server_run_registers_event_handler(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    calls: dict[str, Any] = {"on_event": [], "on_default": 0, "run": 0}

    class _FakeServer:
        def __init__(
            self,
            *,
            app_id: str,
            app_secret: str,
            domain: str = "https://open.feishu.cn",
            timeout_seconds: float = 30.0,
        ) -> None:
            calls["init"] = (app_id, app_secret, domain, timeout_seconds)

        def on_event(self, event_type: str, _handler: Any) -> "_FakeServer":
            calls["on_event"].append(event_type)
            return self

        def on_default(self, _handler: Any) -> "_FakeServer":
            calls["on_default"] += 1
            return self

        def run(self, *, handle_signals: bool = True) -> None:
            calls["run"] += 1
            calls["handle_signals"] = handle_signals

    monkeypatch.setattr(cli, "FeishuBotServer", _FakeServer, raising=False)

    code = cli.main(
        [
            "server",
            "run",
            "--event-type",
            "im.message.receive_v1",
            "--event-type",
            "application.bot.menu_v6",
            "--no-handle-signals",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert calls["init"] == (
        "cli_test_app",
        "cli_test_secret",
        "https://open.feishu.cn",
        30.0,
    )
    assert calls["on_event"] == ["im.message.receive_v1", "application.bot.menu_v6"]
    assert calls["on_default"] == 0
    assert calls["run"] == 1
    assert calls["handle_signals"] is False
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True


def test_ws_run_writes_output_file(
    monkeypatch: Any, tmp_path: Path, capsys: Any
) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    class _FakeWSClient:
        def __init__(
            self,
            *,
            app_id: str,
            app_secret: str,
            handler_registry: Any,
            domain: str = "https://open.feishu.cn",
            timeout_seconds: float = 30.0,
            reconnect_policy: Any = None,
            heartbeat: Any = None,
            http_client: Any = None,
        ) -> None:
            self._registry = handler_registry
            self._stopped = False
            assert app_id == "cli_test_app"
            assert app_secret == "cli_test_secret"
            assert domain == "https://open.feishu.cn"
            assert timeout_seconds == 30.0

        async def start(self) -> None:
            payload = {
                "schema": "2.0",
                "header": {
                    "event_id": "evt_ws_1",
                    "event_type": "im.message.receive_v1",
                },
                "event": {
                    "message": {"message_id": "om_ws_1", "chat_id": "oc_ws_1"},
                    "sender": {"sender_id": {"open_id": "ou_ws_1"}},
                },
            }
            self._registry.dispatch(build_event_context(payload))
            while not self._stopped:
                await asyncio.sleep(0.01)

        async def stop(self) -> None:
            self._stopped = True

    monkeypatch.setattr(cli, "AsyncLongConnectionClient", _FakeWSClient, raising=False)

    output_file = tmp_path / "events.jsonl"
    code = cli.main(
        [
            "ws",
            "run",
            "--max-events",
            "1",
            "--output-file",
            str(output_file),
            "--format",
            "json",
        ]
    )
    assert code == 0
    stdout_lines = capsys.readouterr().out.strip().splitlines()
    event_stdout = json.loads(stdout_lines[0])
    payload = json.loads("\n".join(stdout_lines[1:]))
    assert event_stdout["event_type"] == "im.message.receive_v1"
    assert payload["ok"] is True
    assert payload["events"] == 1
    lines = output_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    event = json.loads(lines[0])
    assert event["event_type"] == "im.message.receive_v1"
    assert event["message_id"] == "om_ws_1"


def test_webhook_serve_invokes_server_runner(monkeypatch: Any, capsys: Any) -> None:
    captured: dict[str, Any] = {}

    def _fake_serve_webhook_http(
        *,
        receiver: Any,
        host: str,
        port: int,
        path: str,
        output_format: str,
        max_requests: int | None,
    ) -> None:
        captured["receiver"] = receiver
        captured["host"] = host
        captured["port"] = port
        captured["path"] = path
        captured["output_format"] = output_format
        captured["max_requests"] = max_requests

    monkeypatch.setattr(
        cli, "_serve_webhook_http", _fake_serve_webhook_http, raising=False
    )

    code = cli.main(
        [
            "webhook",
            "serve",
            "--host",
            "127.0.0.1",
            "--port",
            "18080",
            "--path",
            "webhook/test",
            "--max-requests",
            "2",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 18080
    assert captured["path"] == "/webhook/test"
    assert captured["output_format"] == "json"
    assert captured["max_requests"] == 2
    assert type(captured["receiver"]).__name__ == "WebhookReceiver"
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True


def test_server_start_status_stop(
    monkeypatch: Any, tmp_path: Path, capsys: Any
) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    pid_file = tmp_path / "server.pid"
    captured: dict[str, Any] = {}

    class _Proc:
        pid = 43210

    def _fake_spawn(cmd: list[str], *, log_file: object) -> _Proc:
        captured["cmd"] = cmd
        captured["log_file"] = log_file
        return _Proc()

    monkeypatch.setattr(cli, "_spawn_background_process", _fake_spawn, raising=False)
    monkeypatch.setattr(cli, "_is_process_alive", lambda _pid: False, raising=False)

    start_code = cli.main(
        [
            "server",
            "start",
            "--pid-file",
            str(pid_file),
            "--max-events",
            "2",
            "--event-type",
            "im.message.receive_v1",
            "--format",
            "json",
        ]
    )
    assert start_code == 0
    start_payload = json.loads(capsys.readouterr().out)
    assert start_payload["ok"] is True
    assert start_payload["pid"] == 43210
    assert pid_file.read_text(encoding="utf-8").strip() == "43210"
    assert "server" in " ".join(captured["cmd"])

    monkeypatch.setattr(cli, "_is_process_alive", lambda _pid: True, raising=False)
    status_code = cli.main(
        ["server", "status", "--pid-file", str(pid_file), "--format", "json"]
    )
    assert status_code == 0
    status_payload = json.loads(capsys.readouterr().out)
    assert status_payload["running"] is True
    assert status_payload["pid"] == 43210

    stopped: dict[str, Any] = {}

    def _fake_terminate(pid: int) -> None:
        stopped["pid"] = pid

    monkeypatch.setattr(cli, "_terminate_process", _fake_terminate, raising=False)
    stop_code = cli.main(
        ["server", "stop", "--pid-file", str(pid_file), "--format", "json"]
    )
    assert stop_code == 0
    stop_payload = json.loads(capsys.readouterr().out)
    assert stop_payload["ok"] is True
    assert stop_payload["stopped"] is True
    assert stopped["pid"] == 43210
    assert not pid_file.exists()
