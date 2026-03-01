import asyncio
import argparse
import io
import json
import time
from pathlib import Path
from typing import Any

from feishu_bot_sdk import cli
from feishu_bot_sdk.bot import BotService
from feishu_bot_sdk.bitable import BitableService
from feishu_bot_sdk.config import FeishuConfig
from feishu_bot_sdk.drive_permissions import DrivePermissionService
from feishu_bot_sdk.events import build_event_context
from feishu_bot_sdk.im.messages import MessageService
from feishu_bot_sdk.webhook.security import compute_signature
from feishu_bot_sdk.wiki import WikiService
from feishu_bot_sdk.ws.endpoint import WSEndpoint, WSRemoteConfig


def _base_args(**overrides: Any) -> argparse.Namespace:
    data: dict[str, Any] = {
        "app_id": None,
        "app_secret": None,
        "tenant_access_token": None,
        "base_url": None,
        "timeout": None,
    }
    data.update(overrides)
    return argparse.Namespace(**data)


def test_build_config_prefers_env_credentials(monkeypatch: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "env_app_id")
    monkeypatch.setenv("FEISHU_APP_SECRET", "env_app_secret")

    config = cli._build_config(_base_args(app_id="arg_app_id", app_secret="arg_app_secret"))

    assert isinstance(config, FeishuConfig)
    assert config.app_id == "env_app_id"
    assert config.app_secret == "env_app_secret"


def test_auth_token_json_output(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    monkeypatch.setattr(
        "feishu_bot_sdk.feishu.FeishuClient.get_tenant_access_token",
        lambda _self: "t-env",
    )

    code = cli.main(["auth", "token", "--format", "json"])
    assert code == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["tenant_access_token"] == "t-env"


def test_auth_request_payload_from_stdin(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")
    monkeypatch.setattr("sys.stdin", io.StringIO('{"x": 1}'))

    captured: dict[str, Any] = {}

    def _fake_request_json(
        _self: Any,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        captured["method"] = method
        captured["path"] = path
        captured["payload"] = payload
        captured["params"] = params
        return {"code": 0, "echo": payload}

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)

    code = cli.main(["auth", "request", "POST", "/x/y", "--payload-stdin", "--format", "json"])
    assert code == 0
    assert captured["method"] == "POST"
    assert captured["path"] == "/x/y"
    assert captured["payload"] == {"x": 1}
    payload = json.loads(capsys.readouterr().out)
    assert payload["echo"] == {"x": 1}


def test_bot_info_json_output(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    def _fake_get_info(_self: BotService) -> dict[str, Any]:
        return {
            "app_name": "CLI Bot",
            "open_id": "ou_cli_bot_1",
        }

    monkeypatch.setattr("feishu_bot_sdk.bot.BotService.get_info", _fake_get_info)

    code = cli.main(["bot", "info", "--format", "json"])
    assert code == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["app_name"] == "CLI Bot"
    assert payload["open_id"] == "ou_cli_bot_1"


def test_im_send_markdown_reads_file(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    captured: dict[str, Any] = {}

    def _fake_send_markdown(
        _self: MessageService,
        *,
        receive_id_type: str,
        receive_id: str,
        markdown: str,
        locale: str = "zh_cn",
        title: str | None = None,
        uuid: str | None = None,
    ) -> dict[str, str]:
        captured["receive_id_type"] = receive_id_type
        captured["receive_id"] = receive_id
        captured["markdown"] = markdown
        captured["locale"] = locale
        captured["title"] = title
        captured["uuid"] = uuid
        return {"message_id": "om_cli_1"}

    monkeypatch.setattr("feishu_bot_sdk.im.messages.MessageService.send_markdown", _fake_send_markdown)

    markdown_file = tmp_path / "sample.md"
    markdown_file.write_text("### hello from file", encoding="utf-8")

    code = cli.main(
        [
            "im",
            "send-markdown",
            "--receive-id",
            "ou_1",
            "--markdown-file",
            str(markdown_file),
        ]
    )
    assert code == 0
    assert captured["receive_id_type"] == "open_id"
    assert captured["receive_id"] == "ou_1"
    assert captured["markdown"] == "### hello from file"

    stdout = capsys.readouterr().out
    assert "message_id" in stdout
    assert "om_cli_1" in stdout


def test_im_send_markdown_requires_input(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    code = cli.main(
        [
            "im",
            "send-markdown",
            "--receive-id",
            "ou_1",
        ]
    )
    assert code == 2

    stderr = capsys.readouterr().err
    assert "exactly one of --markdown, --markdown-file or --markdown-stdin is required" in stderr


def test_im_send_markdown_from_stdin(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")
    monkeypatch.setattr("sys.stdin", io.StringIO("### stdin markdown"))

    captured: dict[str, Any] = {}

    def _fake_send_markdown(
        _self: MessageService,
        *,
        receive_id_type: str,
        receive_id: str,
        markdown: str,
        locale: str = "zh_cn",
        title: str | None = None,
        uuid: str | None = None,
    ) -> dict[str, str]:
        captured["markdown"] = markdown
        return {"message_id": "om_stdin_1"}

    monkeypatch.setattr("feishu_bot_sdk.im.messages.MessageService.send_markdown", _fake_send_markdown)

    code = cli.main(
        [
            "im",
            "send-markdown",
            "--receive-id",
            "ou_1",
            "--markdown-stdin",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert captured["markdown"] == "### stdin markdown"
    payload = json.loads(capsys.readouterr().out)
    assert payload["message_id"] == "om_stdin_1"


def test_bitable_create_from_csv_with_grant(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    called: dict[str, Any] = {}

    def _fake_create_from_csv(
        _self: BitableService,
        csv_path: str,
        app_name: str,
        table_name: str,
    ) -> tuple[str, str]:
        called["csv_path"] = csv_path
        called["app_name"] = app_name
        called["table_name"] = table_name
        return "app_token_1", "https://example.com/base/app_token_1"

    def _fake_grant(_self: BitableService, app_token: str, member_id: str, member_id_type: str) -> None:
        called["grant"] = (app_token, member_id, member_id_type)

    monkeypatch.setattr("feishu_bot_sdk.bitable.BitableService.create_from_csv", _fake_create_from_csv)
    monkeypatch.setattr("feishu_bot_sdk.bitable.BitableService.grant_edit_permission", _fake_grant)

    code = cli.main(
        [
            "bitable",
            "create-from-csv",
            "final.csv",
            "--app-name",
            "A",
            "--table-name",
            "T",
            "--grant-member-id",
            "ou_1",
        ]
    )
    assert code == 0
    assert called["csv_path"] == "final.csv"
    assert called["app_name"] == "A"
    assert called["table_name"] == "T"
    assert called["grant"] == ("app_token_1", "ou_1", "open_id")
    assert "app_token" in capsys.readouterr().out


def test_docx_get_markdown_json_output(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    monkeypatch.setattr(
        "feishu_bot_sdk.docs_content.DocContentService.get_markdown",
        lambda _self, doc_token, doc_type="docx", lang=None: f"{doc_token}:{doc_type}:{lang}",
    )

    code = cli.main(
        [
            "docx",
            "get-markdown",
            "--doc-token",
            "doccn_xxx",
            "--format",
            "json",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["markdown"] == "doccn_xxx:docx:None"


def test_drive_grant_edit(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    called: dict[str, Any] = {}

    def _fake_grant_edit_permission(
        _self: DrivePermissionService,
        token: str,
        member_id: str,
        member_id_type: str = "open_id",
        *,
        resource_type: str,
        permission: str,
    ) -> None:
        called["args"] = (token, member_id, member_id_type, resource_type, permission)

    monkeypatch.setattr(
        "feishu_bot_sdk.drive_permissions.DrivePermissionService.grant_edit_permission",
        _fake_grant_edit_permission,
    )

    code = cli.main(
        [
            "drive",
            "grant-edit",
            "--token",
            "tok_1",
            "--resource-type",
            "docx",
            "--member-id",
            "ou_1",
            "--permission",
            "edit",
        ]
    )
    assert code == 0
    assert called["args"] == ("tok_1", "ou_1", "open_id", "docx", "edit")
    assert "ok" in capsys.readouterr().out


def test_wiki_search_nodes(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    def _fake_search_nodes(
        _self: WikiService,
        query: str,
        *,
        space_id: str | None = None,
        node_id: str | None = None,
        page_size: int | None = None,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        return {
            "items": [{"title": "node-1", "query": query}],
            "space_id": space_id,
            "node_id": node_id,
            "page_size": page_size,
            "page_token": page_token,
        }

    monkeypatch.setattr("feishu_bot_sdk.wiki.WikiService.search_nodes", _fake_search_nodes)

    code = cli.main(
        [
            "wiki",
            "search-nodes",
            "--query",
            "weekly",
            "--space-id",
            "sp_1",
            "--page-size",
            "10",
            "--format",
            "json",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["space_id"] == "sp_1"
    assert payload["page_size"] == 10
    assert payload["items"][0]["query"] == "weekly"


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

    monkeypatch.setattr("feishu_bot_sdk.cli.fetch_ws_endpoint", _fake_fetch_ws_endpoint)

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

    monkeypatch.setattr("feishu_bot_sdk.cli.FeishuBotServer", _FakeServer)

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
    assert calls["init"] == ("cli_test_app", "cli_test_secret", "https://open.feishu.cn", 30.0)
    assert calls["on_event"] == ["im.message.receive_v1", "application.bot.menu_v6"]
    assert calls["on_default"] == 0
    assert calls["run"] == 1
    assert calls["handle_signals"] is False
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True


def test_ws_run_writes_output_file(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
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
                "header": {"event_id": "evt_ws_1", "event_type": "im.message.receive_v1"},
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

    monkeypatch.setattr("feishu_bot_sdk.cli.AsyncLongConnectionClient", _FakeWSClient)

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

    monkeypatch.setattr("feishu_bot_sdk.cli._serve_webhook_http", _fake_serve_webhook_http)

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


def test_server_start_status_stop(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
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

    monkeypatch.setattr("feishu_bot_sdk.cli._spawn_background_process", _fake_spawn)
    monkeypatch.setattr("feishu_bot_sdk.cli._is_process_alive", lambda _pid: False)

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

    monkeypatch.setattr("feishu_bot_sdk.cli._is_process_alive", lambda _pid: True)
    status_code = cli.main(["server", "status", "--pid-file", str(pid_file), "--format", "json"])
    assert status_code == 0
    status_payload = json.loads(capsys.readouterr().out)
    assert status_payload["running"] is True
    assert status_payload["pid"] == 43210

    stopped: dict[str, Any] = {}

    def _fake_terminate(pid: int) -> None:
        stopped["pid"] = pid

    monkeypatch.setattr("feishu_bot_sdk.cli._terminate_process", _fake_terminate)
    stop_code = cli.main(["server", "stop", "--pid-file", str(pid_file), "--format", "json"])
    assert stop_code == 0
    stop_payload = json.loads(capsys.readouterr().out)
    assert stop_payload["ok"] is True
    assert stop_payload["stopped"] is True
    assert stopped["pid"] == 43210
    assert not pid_file.exists()
