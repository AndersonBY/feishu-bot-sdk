import json
from typing import Any

from click.testing import CliRunner

import feishu_bot_sdk.cli as cli_module
from feishu_bot_sdk.cli.app import app


def test_server_run_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["server", "run", "--help"])
    assert result.exit_code == 0
    assert "--max-events" in result.output
    assert "--no-handle-signals" in result.output
    assert "--event-type" in result.output
    assert "--domain" in result.output


def test_server_start_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["server", "start", "--help"])
    assert result.exit_code == 0
    assert "--pid-file" in result.output
    assert "--log-file" in result.output
    assert "--max-events" in result.output


def test_server_status_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["server", "status", "--help"])
    assert result.exit_code == 0
    assert "--pid-file" in result.output


def test_server_stop_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["server", "stop", "--help"])
    assert result.exit_code == 0
    assert "--pid-file" in result.output


def test_server_run_registers_handler(monkeypatch: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    calls: dict[str, Any] = {"on_event": [], "on_default": 0, "run": 0}

    class _FakeServer:
        def __init__(self, *, app_id: str, app_secret: str, domain: str = "https://open.feishu.cn", timeout_seconds: float = 30.0) -> None:
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

    monkeypatch.setattr(cli_module, "FeishuBotServer", _FakeServer, raising=False)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "server",
            "run",
            "--event-type",
            "im.message.receive_v1",
            "--no-handle-signals",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert calls["on_event"] == ["im.message.receive_v1"]
    assert calls["run"] == 1
    assert calls["handle_signals"] is False
