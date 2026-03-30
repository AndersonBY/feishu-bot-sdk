import json
import time
from typing import Any

from click.testing import CliRunner

import feishu_bot_sdk.cli as cli_module
from feishu_bot_sdk.cli.app import app
from feishu_bot_sdk.webhook.security import compute_signature


def test_webhook_decode(monkeypatch: Any) -> None:
    runner = CliRunner()
    body = '{"schema":"2.0","header":{"event_type":"im.message.receive_v1"}}'
    result = runner.invoke(app, ["webhook", "decode", "--body-json", body, "--format", "json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["header"]["event_type"] == "im.message.receive_v1"


def test_webhook_verify_signature() -> None:
    runner = CliRunner()
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
    result = runner.invoke(
        app,
        [
            "webhook",
            "verify-signature",
            "--headers-json",
            json.dumps(headers),
            "--body-json",
            body,
            "--encrypt-key",
            encrypt_key,
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True


def test_webhook_challenge() -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["webhook", "challenge", "--challenge", "test-challenge-token", "--format", "json"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["challenge"] == "test-challenge-token"


def test_webhook_parse() -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "webhook",
            "parse",
            "--body-json",
            '{"schema":"2.0","header":{"event_id":"evt_1","event_type":"application.bot.menu_v6"}}',
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["schema"] == "p2"
    assert payload["event_type"] == "application.bot.menu_v6"
    assert payload["event_id"] == "evt_1"


def test_webhook_serve(monkeypatch: Any) -> None:
    captured: dict[str, Any] = {}

    def _fake_serve(
        *,
        receiver: Any,
        host: str,
        port: int,
        path: str,
        output_format: str,
        max_requests: int | None,
    ) -> None:
        captured["host"] = host
        captured["port"] = port
        captured["path"] = path
        captured["max_requests"] = max_requests

    monkeypatch.setattr(
        cli_module, "_serve_webhook_http", _fake_serve, raising=False
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "webhook",
            "serve",
            "--host",
            "0.0.0.0",
            "--port",
            "9000",
            "--path",
            "/webhook/test",
            "--max-requests",
            "5",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert captured["host"] == "0.0.0.0"
    assert captured["port"] == 9000
    assert captured["path"] == "/webhook/test"
    assert captured["max_requests"] == 5
