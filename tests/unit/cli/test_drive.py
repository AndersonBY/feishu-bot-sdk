import json
from pathlib import Path
from typing import Any
from feishu_bot_sdk import cli
from feishu_bot_sdk.drive import DrivePermissionService


def test_drive_meta_command(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    captured: dict[str, Any] = {}

    def _fake_batch_query_metas(
        _self: Any,
        request_docs: list[dict[str, Any]],
        *,
        with_url: bool | None = None,
        user_id_type: str | None = None,
    ) -> dict[str, Any]:
        captured["request_docs"] = request_docs
        captured["with_url"] = with_url
        captured["user_id_type"] = user_id_type
        return {"metas": [{"doc_token": "doc_1"}]}

    monkeypatch.setattr(
        "feishu_bot_sdk.drive.DriveFileService.batch_query_metas",
        _fake_batch_query_metas,
    )

    code = cli.main(
        [
            "drive",
            "meta",
            "--request-docs-json",
            '[{"doc_token":"doc_1","doc_type":"docx"}]',
            "--with-url",
            "true",
            "--user-id-type",
            "open_id",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert captured == {
        "request_docs": [{"doc_token": "doc_1", "doc_type": "docx"}],
        "with_url": True,
        "user_id_type": "open_id",
    }
    payload = json.loads(capsys.readouterr().out)
    assert payload["metas"][0]["doc_token"] == "doc_1"


def test_drive_download_file_writes_output(
    monkeypatch: Any, tmp_path: Path, capsys: Any
) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    monkeypatch.setattr(
        "feishu_bot_sdk.drive.DriveFileService.download_file",
        lambda _self, file_token: b"downloaded-bytes",
    )

    output = tmp_path / "download.bin"
    code = cli.main(
        [
            "drive",
            "download-file",
            "file_1",
            "--output",
            str(output),
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert output.read_bytes() == b"downloaded-bytes"
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["size"] == len(b"downloaded-bytes")


def test_drive_version_list_all(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    calls: list[str | None] = []

    def _fake_list_versions(
        _self: Any,
        file_token: str,
        *,
        obj_type: str,
        page_size: int,
        page_token: str | None = None,
        user_id_type: str | None = None,
    ) -> dict[str, Any]:
        assert file_token == "doc_1"
        assert obj_type == "docx"
        calls.append(page_token)
        if page_token == "next_v":
            return {"items": [{"version_id": "v2"}], "has_more": False}
        return {
            "items": [{"version_id": "v1"}],
            "has_more": True,
            "page_token": "next_v",
        }

    monkeypatch.setattr(
        "feishu_bot_sdk.drive.DriveFileService.list_versions", _fake_list_versions
    )

    code = cli.main(
        [
            "drive",
            "version-list",
            "doc_1",
            "--obj-type",
            "docx",
            "--page-size",
            "1",
            "--all",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert calls == [None, "next_v"]
    payload = json.loads(capsys.readouterr().out)
    assert payload["all"] is True
    assert payload["count"] == 2
    assert [item["version_id"] for item in payload["items"]] == ["v1", "v2"]


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
        "feishu_bot_sdk.drive.DrivePermissionService.grant_edit_permission",
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


def test_drive_grant_edit_rejects_invalid_permission(capsys: Any) -> None:
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
            "owner",
        ]
    )
    assert code == 2
    assert "invalid choice" in capsys.readouterr().err
