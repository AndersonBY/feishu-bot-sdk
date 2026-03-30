import json
from typing import Any
from feishu_bot_sdk import cli


def test_drive_requester_upload_file_creates_child_folder_and_verifies_owner(
    monkeypatch: Any, capsys: Any
) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")
    monkeypatch.setenv("FEISHU_USER_ACCESS_TOKEN", "user_access_token_x")

    class _FakeUserInfo:
        open_id = "ou_current"
        user_id = "cli_current"
        union_id = "on_current"
        name = "Current User"

    captured: dict[str, Any] = {}

    monkeypatch.setattr(
        "feishu_bot_sdk.feishu.FeishuClient.get_user_info",
        lambda _self, user_access_token=None: _FakeUserInfo(),
    )
    monkeypatch.setattr(
        "feishu_bot_sdk.drive.DriveFileService.get_root_folder_meta",
        lambda _self: {"token": "fld_root_requester"},
    )

    def _fake_create_folder(_self: Any, *, name: str, folder_token: str) -> dict[str, Any]:
        captured["folder_name"] = name
        captured["folder_token"] = folder_token
        return {"token": "fld_child_requester"}

    monkeypatch.setattr("feishu_bot_sdk.drive.DriveFileService.create_folder", _fake_create_folder)

    def _fake_upload_file(
        _self: Any,
        path: str,
        *,
        parent_type: str,
        parent_node: str,
        file_name: str | None = None,
        checksum: str | None = None,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        captured["upload"] = {
            "path": path,
            "parent_type": parent_type,
            "parent_node": parent_node,
            "file_name": file_name,
            "checksum": checksum,
            "content_type": content_type,
        }
        return {"file_token": "file_uploaded_requester"}

    monkeypatch.setattr("feishu_bot_sdk.drive.DriveFileService.upload_file", _fake_upload_file)
    monkeypatch.setattr(
        "feishu_bot_sdk.drive.DriveFileService.batch_query_metas",
        lambda _self, request_docs, with_url=None, user_id_type=None: {
            "metas": [
                {
                    "doc_token": "file_uploaded_requester",
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
            "+requester-upload",
            "report.docx",
            "--folder-name",
            "Requester Upload Test",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert captured == {
        "folder_name": "Requester Upload Test",
        "folder_token": "fld_root_requester",
        "upload": {
            "path": "report.docx",
            "parent_type": "explorer",
            "parent_node": "fld_child_requester",
            "file_name": None,
            "checksum": None,
            "content_type": None,
        },
    }
    payload = json.loads(capsys.readouterr().out)
    assert payload["workflow"] == "requester_upload_file"
    assert payload["root_folder"]["token"] == "fld_root_requester"
    assert payload["created_folder"]["token"] == "fld_child_requester"
    assert payload["file_token"] == "file_uploaded_requester"
    diagnostics = payload["_cli_diagnostics"]
    assert diagnostics["requester_owner_verified"] is True
    assert diagnostics["ownership_checks"][0]["owner_match_field"] == "open_id"


def test_drive_requester_upload_file_fails_when_owner_mismatches(
    monkeypatch: Any, capsys: Any
) -> None:
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
        "feishu_bot_sdk.drive.DriveFileService.get_root_folder_meta",
        lambda _self: {"token": "fld_root_requester"},
    )
    monkeypatch.setattr(
        "feishu_bot_sdk.drive.DriveFileService.create_folder",
        lambda _self, *, name, folder_token: {"token": "fld_child_requester"},
    )
    monkeypatch.setattr(
        "feishu_bot_sdk.drive.DriveFileService.upload_file",
        lambda _self, path, parent_type, parent_node, file_name=None, checksum=None, content_type=None: {
            "file_token": "file_uploaded_requester"
        },
    )
    monkeypatch.setattr(
        "feishu_bot_sdk.drive.DriveFileService.batch_query_metas",
        lambda _self, request_docs, with_url=None, user_id_type=None: {
            "metas": [
                {
                    "doc_token": "file_uploaded_requester",
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
            "+requester-upload",
            "report.docx",
            "--folder-name",
            "Requester Upload Test",
            "--format",
            "json",
        ]
    )
    assert code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["exit_code"] == 2
    assert "requester-owned upload owner verification failed" in payload["error"]["message"]
    assert "file_token=file_uploaded_requester" in payload["error"]["message"]
    assert "created_folder_token=fld_child_requester" in payload["error"]["message"]
