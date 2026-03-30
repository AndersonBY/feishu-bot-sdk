from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from click.testing import CliRunner

from feishu_bot_sdk.cli.app import app
from feishu_bot_sdk.token_store import StoredUserToken, TokenStore


def _configure_cli_paths(monkeypatch: Any, tmp_path: Path) -> tuple[Path, Path, Path]:
    config_path = tmp_path / "config" / "cli-config.json"
    secret_store_path = tmp_path / "config" / "cli-secrets.json"
    secret_key_path = tmp_path / "config" / "cli-secrets.key"
    monkeypatch.setenv("FEISHU_CLI_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("FEISHU_SECRET_STORE_PATH", str(secret_store_path))
    monkeypatch.setenv("FEISHU_SECRET_STORE_KEY_PATH", str(secret_key_path))
    monkeypatch.setenv("FEISHU_SECRET_STORE_BACKEND", "encrypted_file")
    return config_path, secret_store_path, secret_key_path


def test_root_help_lists_new_top_level_commands() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "api" in result.output
    assert "schema" in result.output
    assert "doctor" in result.output
    assert "completion" in result.output
    assert "calendar" in result.output


def test_completion_help_does_not_expose_runtime_auth_options() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["completion", "--help"])
    assert result.exit_code == 0
    assert "--format" in result.output
    assert "--profile" not in result.output
    assert "--app-id" not in result.output
    assert "--as" not in result.output


def test_schema_show_service_method_and_shortcut() -> None:
    runner = CliRunner()

    method_result = runner.invoke(app, ["schema", "show", "drive.files.copy", "--format", "json"])
    assert method_result.exit_code == 0
    method_payload = json.loads(method_result.output)
    assert method_payload["type"] == "service_method"
    assert method_payload["schema_path"] == "drive.files.copy"
    assert method_payload["path"].endswith("/drive/v1/files/{file_token}/copy")

    shortcut_result = runner.invoke(app, ["schema", "show", "drive.+requester-upload", "--format", "json"])
    assert shortcut_result.exit_code == 0
    shortcut_payload = json.loads(shortcut_result.output)
    assert shortcut_payload["type"] == "shortcut"
    assert shortcut_payload["risk"] == "write"


def test_generated_service_command_executes_and_substitutes_path(monkeypatch: Any) -> None:
    runner = CliRunner()
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
        return {"ok": True, "path": path}

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)

    result = runner.invoke(
        app,
        [
            "drive",
            "files",
            "copy",
            "--params",
            '{"file_token":"doc_1","user_id_type":"open_id"}',
            "--data",
            '{"folder_token":"fld_1","name":"copy","type":"file"}',
            "--app-id",
            "cli_app",
            "--app-secret",
            "cli_secret",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert captured == {
        "method": "POST",
        "path": "/open-apis/drive/v1/files/doc_1/copy",
        "payload": {"folder_token": "fld_1", "name": "copy", "type": "file"},
        "params": {"user_id_type": "open_id"},
    }


def test_api_dry_run_and_shortcut_dry_run() -> None:
    runner = CliRunner()

    api_result = runner.invoke(
        app,
        [
            "api",
            "POST",
            "/open-apis/drive/v1/files",
            "--params",
            '{"folder_token":"fld_1"}',
            "--data",
            '{"name":"demo"}',
            "--dry-run",
            "--format",
            "json",
        ],
    )
    assert api_result.exit_code == 0
    api_payload = json.loads(api_result.output)
    assert api_payload["dry_run"] is True
    assert api_payload["request"]["method"] == "POST"

    shortcut_result = runner.invoke(
        app,
        [
            "docx",
            "+insert-content",
            "--document-id",
            "doc_123",
            "--content",
            "# Hello",
            "--dry-run",
            "--format",
            "json",
        ],
    )
    assert shortcut_result.exit_code == 0
    shortcut_payload = json.loads(shortcut_result.output)
    assert shortcut_payload["dry_run"] is True
    assert shortcut_payload["shortcut"] == "docx.+insert-content"


def test_docx_create_help_and_execution(monkeypatch: Any) -> None:
    runner = CliRunner()
    captured: dict[str, Any] = {}

    def _fake_create_document(self: Any, title: str, *, folder_token: str | None = None) -> dict[str, Any]:
        captured["title"] = title
        captured["folder_token"] = folder_token
        return {"document": {"document_id": "doc_123", "title": title}}

    monkeypatch.setattr(
        "feishu_bot_sdk.docx.DocxService.create_document",
        _fake_create_document,
    )

    help_result = runner.invoke(app, ["docx", "create", "--help"])
    assert help_result.exit_code == 0
    assert "--title" in help_result.output
    assert "--folder-token" in help_result.output

    run_result = runner.invoke(
        app,
        [
            "docx",
            "create",
            "--title",
            "日报",
            "--folder-token",
            "fld_123",
            "--app-id",
            "cli_app",
            "--app-secret",
            "cli_secret",
            "--format",
            "json",
        ],
    )
    assert run_result.exit_code == 0
    assert captured == {"title": "日报", "folder_token": "fld_123"}
    payload = json.loads(run_result.output)
    assert payload["document"]["document_id"] == "doc_123"


def test_config_set_default_as_and_auth_status(monkeypatch: Any, tmp_path: Path) -> None:
    _configure_cli_paths(monkeypatch, tmp_path)
    runner = CliRunner()
    token_store_path = tmp_path / "tokens.json"

    init_result = runner.invoke(
        app,
        [
            "config",
            "init",
            "--profile",
            "work",
            "--app-id",
            "cli_work",
            "--app-secret-stdin",
            "--token-store",
            str(token_store_path),
            "--format",
            "json",
        ],
        input="secret-value\n",
    )
    assert init_result.exit_code == 0

    set_default_as_result = runner.invoke(
        app,
        [
            "config",
            "set-default-as",
            "--profile",
            "work",
            "--as",
            "user",
            "--format",
            "json",
        ],
    )
    assert set_default_as_result.exit_code == 0
    set_default_as_payload = json.loads(set_default_as_result.output)
    assert set_default_as_payload["default_as"] == "user"

    TokenStore(token_store_path).save_profile(
        "work",
        StoredUserToken(
            access_token="user_access",
            refresh_token="user_refresh",
            expires_at=4102444800.0,
            refresh_expires_at=4102445800.0,
            scope="drive:file:upload docs:doc",
        ),
    )

    status_result = runner.invoke(
        app,
        [
            "auth",
            "status",
            "--profile",
            "work",
            "--token-store",
            str(token_store_path),
            "--format",
            "json",
        ],
    )
    assert status_result.exit_code == 0
    status_payload = json.loads(status_result.output)
    assert status_payload["default_as"] == "user"
    assert status_payload["user_token_status"] == "valid"
    assert "drive:file:upload" in status_payload["granted_scopes"]

    check_result = runner.invoke(
        app,
        [
            "auth",
            "check",
            "--profile",
            "work",
            "--token-store",
            str(token_store_path),
            "--scope",
            "drive:file:upload docs:doc mail:message:send",
            "--format",
            "json",
        ],
    )
    assert check_result.exit_code == 0
    check_payload = json.loads(check_result.output)
    assert check_payload["ok"] is False
    assert check_payload["missing_scopes"] == ["mail:message:send"]


def test_doctor_offline_and_completion(monkeypatch: Any, tmp_path: Path) -> None:
    _configure_cli_paths(monkeypatch, tmp_path)
    runner = CliRunner()

    init_result = runner.invoke(
        app,
        [
            "config",
            "init",
            "--profile",
            "default",
            "--app-id",
            "cli_app",
            "--app-secret-stdin",
            "--format",
            "json",
        ],
        input="secret-value\n",
    )
    assert init_result.exit_code == 0

    doctor_result = runner.invoke(app, ["doctor", "--offline", "--format", "json"])
    assert doctor_result.exit_code == 0
    doctor_payload = json.loads(doctor_result.output)
    assert any(item["name"] == "metadata" for item in doctor_payload["checks"])

    completion_result = runner.invoke(app, ["completion", "bash", "--format", "json"])
    assert completion_result.exit_code == 0
    completion_payload = json.loads(completion_result.output)
    assert completion_payload["shell"] == "bash"
    assert "_FEISHU_COMPLETE" in completion_payload["script"]
