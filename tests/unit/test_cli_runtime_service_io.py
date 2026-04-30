from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from click.testing import CliRunner

from feishu_bot_sdk.cli.app import app, main


def test_service_command_accepts_at_file_json_and_jq_filter(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    params_path = tmp_path / "params.json"
    data_path = tmp_path / "data.json"
    params_path.write_text(
        json.dumps({"file_token": "doc_1", "user_id_type": "open_id"}),
        encoding="utf-8",
    )
    data_path.write_text(
        json.dumps({"folder_token": "fld_1", "name": "copy", "type": "file"}),
        encoding="utf-8",
    )
    captured: dict[str, Any] = {}

    def _fake_request_json(
        _self: Any,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        captured.update({"method": method, "path": path, "payload": payload, "params": params})
        return {"code": 0, "data": {"copied_token": "doc_copy"}}

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)

    result = CliRunner().invoke(
        app,
        [
            "drive",
            "files",
            "copy",
            "--params",
            f"@{params_path}",
            "--data",
            f"@{data_path}",
            "--jq",
            ".data.copied_token",
            "--yes",
            "--app-id",
            "cli_app",
            "--app-secret",
            "cli_secret",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == "doc_copy"
    assert captured == {
        "method": "POST",
        "path": "/open-apis/drive/v1/files/doc_1/copy",
        "payload": {"folder_token": "fld_1", "name": "copy", "type": "file"},
        "params": {"user_id_type": "open_id"},
    }


def test_service_high_risk_requires_yes_but_dry_run_skips_confirmation(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    called = False

    def _fake_request_json(
        _self: Any,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        nonlocal called
        called = True
        return {"code": 0, "method": method, "path": path, "payload": payload, "params": params}

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)
    runner = CliRunner()
    base_args = [
        "im",
        "chat.members",
        "create",
        "--params",
        '{"chat_id":"oc_1","member_id_type":"open_id"}',
        "--data",
        '{"id_list":["ou_1"]}',
        "--app-id",
        "cli_app",
        "--app-secret",
        "cli_secret",
        "--format",
        "json",
    ]

    assert main(base_args) == 2
    blocked_payload = json.loads(capsys.readouterr().out)
    assert blocked_payload["ok"] is False
    assert "requires --yes" in blocked_payload["error"]["message"]
    assert called is False

    dry_run = runner.invoke(app, [*base_args, "--dry-run"])
    assert dry_run.exit_code == 0, dry_run.output
    dry_run_payload = json.loads(dry_run.output)
    assert dry_run_payload["dry_run"] is True
    assert dry_run_payload["risk"] == {
        "risk": "high-risk-write",
        "requires_confirmation": True,
    }

    confirmed = runner.invoke(app, [*base_args, "--yes"])
    assert confirmed.exit_code == 0, confirmed.output
    assert called is True


def test_service_rejects_output_with_page_all_before_auth(capsys: Any) -> None:
    exit_code = main(
        [
            "drive",
            "file.comments",
            "list",
            "--page-all",
            "--output",
            "files.json",
            "--format",
            "json",
        ],
    )

    assert exit_code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"]["type"] == "validation_error"
    assert "--output and --page-all are mutually exclusive" in payload["error"]["message"]


def test_api_accepts_stdin_json_and_rejects_output_with_page_all(capsys: Any) -> None:
    runner = CliRunner()

    dry_run = runner.invoke(
        app,
        [
            "api",
            "POST",
            "/open-apis/test",
            "--data",
            "-",
            "--dry-run",
            "--format",
            "json",
        ],
        input='{"hello":"world"}',
    )

    assert dry_run.exit_code == 0, dry_run.output
    dry_run_payload = json.loads(dry_run.output)
    assert dry_run_payload["request"]["data"] == {"hello": "world"}

    exit_code = main(
        [
            "api",
            "GET",
            "/open-apis/test",
            "--page-all",
            "--output",
            "body.bin",
            "--format",
            "json",
        ],
    )

    assert exit_code == 2
    conflict_payload = json.loads(capsys.readouterr().out)
    assert "--output and --page-all are mutually exclusive" in conflict_payload["error"]["message"]


def test_api_file_upload_dry_run_and_execution(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "avatar.png"
    image_path.write_bytes(b"png-bytes")
    captured: dict[str, Any] = {}

    def _fake_request_multipart(
        _self: Any,
        method: str,
        path: str,
        *,
        data: dict[str, Any] | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        captured.update(
            {
                "method": method,
                "path": path,
                "data": data,
                "files": files,
                "params": params,
            }
        )
        return {"code": 0, "data": {"image_key": "img_1"}}

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_multipart", _fake_request_multipart)
    runner = CliRunner()

    dry_run = runner.invoke(
        app,
        [
            "api",
            "POST",
            "/open-apis/im/v1/images",
            "--data",
            '{"image_type":"message"}',
            "--file",
            f"image={image_path}",
            "--dry-run",
            "--format",
            "json",
        ],
    )
    assert dry_run.exit_code == 0, dry_run.output
    dry_run_payload = json.loads(dry_run.output)
    assert dry_run_payload["request"]["file"] == {
        "field": "image",
        "path": str(image_path),
        "mime_type": "image/png",
    }

    result = runner.invoke(
        app,
        [
            "api",
            "POST",
            "/open-apis/im/v1/images",
            "--data",
            '{"image_type":"message"}',
            "--file",
            f"image={image_path}",
            "--app-id",
            "cli_app",
            "--app-secret",
            "cli_secret",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["data"]["image_key"] == "img_1"
    assert captured["method"] == "POST"
    assert captured["path"] == "/open-apis/im/v1/images"
    assert captured["data"] == {"image_type": "message"}
    assert captured["files"] == {
        "image": ("avatar.png", b"png-bytes", "image/png"),
    }


def test_service_file_upload_dry_run_detects_default_field(tmp_path: Path) -> None:
    image_path = tmp_path / "avatar.png"
    image_path.write_bytes(b"png-bytes")

    result = CliRunner().invoke(
        app,
        [
            "im",
            "images",
            "create",
            "--data",
            '{"image_type":"message"}',
            "--file",
            str(image_path),
            "--dry-run",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["request"]["file"] == {
        "field": "image",
        "path": str(image_path),
        "mime_type": "image/png",
    }
    assert payload["request"]["data"] == {"image_type": "message"}
