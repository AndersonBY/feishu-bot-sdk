import json
from typing import Any

from click.testing import CliRunner

import feishu_bot_sdk.cli as cli_module
from feishu_bot_sdk.cli.app import app
from feishu_bot_sdk.ws.endpoint import WSEndpoint, WSRemoteConfig


def test_ws_endpoint(monkeypatch: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    def _fake_fetch_ws_endpoint(
        *,
        app_id: str,
        app_secret: str,
        domain: str = "https://open.feishu.cn",
        timeout_seconds: float = 30.0,
    ) -> WSEndpoint:
        return WSEndpoint(
            url="wss://example/ws",
            device_id="d1",
            service_id="s1",
            remote_config=WSRemoteConfig(
                reconnect_count=3,
                reconnect_interval_seconds=120.0,
                reconnect_nonce_seconds=30.0,
                ping_interval_seconds=20.0,
            ),
        )

    monkeypatch.setattr(cli_module, "fetch_ws_endpoint", _fake_fetch_ws_endpoint, raising=False)

    runner = CliRunner()
    result = runner.invoke(app, ["ws", "endpoint", "--format", "json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["device_id"] == "d1"
    assert payload["remote_config"]["reconnect_count"] == 3


def test_ws_run_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["ws", "run", "--help"])
    assert result.exit_code == 0
    assert "--max-events" in result.output
    assert "--duration-seconds" in result.output
    assert "--print-payload" in result.output
    assert "--event-type" in result.output
