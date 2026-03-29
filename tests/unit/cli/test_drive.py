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


def test_drive_meta_can_check_requester_owner(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")
    monkeypatch.setenv("FEISHU_USER_ACCESS_TOKEN", "user_access_token_x")

    class _FakeUserInfo:
        open_id = "ou_current"
        user_id = "cli_current"
        union_id = "on_current"
        name = "Current User"

    monkeypatch.setattr(
        "feishu_bot_sdk.feishu.FeishuClient.get_user_info",
        lambda _self, user_access_token=None: _FakeUserInfo(),
    )
    monkeypatch.setattr(
        "feishu_bot_sdk.drive.DriveFileService.batch_query_metas",
        lambda _self, request_docs, with_url=None, user_id_type=None: {
            "metas": [
                {
                    "doc_token": "doc_1",
                    "doc_type": "file",
                    "title": "report.docx",
                    "owner_id": "ou_other",
                    "latest_modify_user": "ou_other",
                }
            ]
        },
    )

    code = cli.main(
        [
            "drive",
            "meta",
            "--request-docs-json",
            '[{"doc_token":"doc_1","doc_type":"file"}]',
            "--check-requester-owner",
            "--auth-mode",
            "user",
            "--format",
            "json",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    diagnostics = payload["_cli_diagnostics"]
    assert diagnostics["requester_identity"]["open_id"] == "ou_current"
    assert diagnostics["requester_owner_verified"] is False
    assert diagnostics["ownership_checks"][0]["owner_matches_requester"] is False
    assert diagnostics["ownership_checks"][0]["verdict"] == "owner_mismatch"


def test_drive_upload_file_can_check_requester_owner(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")
    monkeypatch.setenv("FEISHU_USER_ACCESS_TOKEN", "user_access_token_x")

    class _FakeUserInfo:
        open_id = "ou_current"
        user_id = "cli_current"
        union_id = "on_current"
        name = "Current User"

    monkeypatch.setattr(
        "feishu_bot_sdk.feishu.FeishuClient.get_user_info",
        lambda _self, user_access_token=None: _FakeUserInfo(),
    )
    monkeypatch.setattr(
        "feishu_bot_sdk.drive.DriveFileService.upload_file",
        lambda _self, path, parent_type, parent_node, file_name=None, checksum=None, content_type=None: {
            "file_token": "file_uploaded_1"
        },
    )
    monkeypatch.setattr(
        "feishu_bot_sdk.drive.DriveFileService.batch_query_metas",
        lambda _self, request_docs, with_url=None, user_id_type=None: {
            "metas": [
                {
                    "doc_token": "file_uploaded_1",
                    "doc_type": "file",
                    "title": "report.docx",
                    "owner_id": "ou_current",
                    "latest_modify_user": "ou_current",
                }
            ]
        },
    )

    code = cli.main(
        [
            "drive",
            "upload-file",
            "report.docx",
            "--parent-type",
            "explorer",
            "--parent-node",
            "fld_xxx",
            "--check-requester-owner",
            "--auth-mode",
            "user",
            "--format",
            "json",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    diagnostics = payload["_cli_diagnostics"]
    assert payload["file_token"] == "file_uploaded_1"
    assert diagnostics["requester_owner_verified"] is True
    assert diagnostics["ownership_checks"][0]["owner_matches_requester"] is True
    assert diagnostics["ownership_checks"][0]["owner_match_field"] == "open_id"


def test_drive_root_folder_meta_command(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")
    monkeypatch.setenv("FEISHU_USER_ACCESS_TOKEN", "user_access_token_x")

    monkeypatch.setattr(
        "feishu_bot_sdk.drive.DriveFileService.get_root_folder_meta",
        lambda _self: {
            "token": "fld_root_requester",
            "url": "https://example.com/root",
        },
    )

    code = cli.main(
        [
            "drive",
            "root-folder-meta",
            "--auth-mode",
            "user",
            "--format",
            "json",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["token"] == "fld_root_requester"
    assert payload["url"] == "https://example.com/root"


def test_drive_download_file_writes_output(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
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

    monkeypatch.setattr("feishu_bot_sdk.drive.DriveFileService.list_versions", _fake_list_versions)

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


def test_drive_grant_edit_me_uses_current_user(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")
    monkeypatch.setenv("FEISHU_USER_ACCESS_TOKEN", "user_access_token_x")

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

    class _FakeUserInfo:
        open_id = "ou_current"
        user_id = "cli_user_current"
        union_id = "on_current"

    monkeypatch.setattr(
        "feishu_bot_sdk.drive.DrivePermissionService.grant_edit_permission",
        _fake_grant_edit_permission,
    )
    monkeypatch.setattr(
        "feishu_bot_sdk.feishu.FeishuClient.get_user_info",
        lambda _self, user_access_token=None: _FakeUserInfo(),
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
            "me",
            "--member-id-type",
            "open_id",
            "--permission",
            "edit",
            "--auth-mode",
            "user",
        ]
    )
    assert code == 0
    assert called["args"] == ("tok_1", "ou_current", "open_id", "docx", "edit")
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
