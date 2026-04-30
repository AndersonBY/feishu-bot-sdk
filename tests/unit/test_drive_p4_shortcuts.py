from __future__ import annotations

import json
from typing import Any

import feishu_bot_sdk.cli as cli
from feishu_bot_sdk.feishu import FeishuClient


def test_drive_help_lists_p4_lark_shortcuts(capsys: Any) -> None:
    code = cli.main(["drive", "--help"])

    assert code == 0
    output = capsys.readouterr().out
    for command in (
        "+upload",
        "+download",
        "+delete",
        "+create-folder",
        "+create-shortcut",
        "+add-comment",
        "+apply-permission",
        "+export-download",
        "+search",
    ):
        assert command in output


def test_drive_upload_and_download_build_transport(monkeypatch: Any, tmp_path: Any, capsys: Any) -> None:
    upload_path = tmp_path / "report.txt"
    upload_path.write_text("hello", encoding="utf-8")
    download_path = tmp_path / "downloaded.txt"
    calls: list[dict[str, Any]] = []

    def _fake_request_multipart(
        _self: FeishuClient,
        method: str,
        path: str,
        *,
        data: dict[str, object] | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
        params: dict[str, object] | None = None,
    ) -> dict[str, Any]:
        calls.append({"method": method, "path": path, "data": data, "files": files, "params": params})
        return {"code": 0, "data": {"file_token": "file_1"}}

    class _FakeResponse:
        status_code = 200
        content = b"download-bytes"
        text = ""
        headers = {"content-type": "text/plain"}

        def raise_for_status(self) -> None:
            return None

    class _FakeClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            return None

        def __enter__(self) -> "_FakeClient":
            return self

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
            return False

        def get(self, url: str, headers: dict[str, str] | None = None) -> _FakeResponse:
            assert "drive/v1/files/file_1/download" in url
            return _FakeResponse()

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_multipart", _fake_request_multipart)
    monkeypatch.setattr("feishu_bot_sdk.cli.commands.drive_shortcuts.httpx.Client", _FakeClient)

    assert (
        cli.main(
            [
                "drive",
                "+upload",
                "--as",
                "bot",
                "--app-id",
                "cli_app",
                "--app-secret",
                "cli_secret",
                "--file",
                str(upload_path),
                "--folder-token",
                "fld_1",
                "--name",
                "renamed.txt",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert (
        cli.main(
            [
                "drive",
                "+download",
                "--as",
                "bot",
                "--access-token",
                "tenant_token",
                "--file-token",
                "file_1",
                "--output",
                str(download_path),
                "--format",
                "json",
            ]
        )
        == 0
    )

    assert calls[0]["method"] == "POST"
    assert calls[0]["path"] == "/drive/v1/files/upload_all"
    assert calls[0]["data"] == {
        "file_name": "renamed.txt",
        "parent_type": "explorer",
        "parent_node": "fld_1",
        "size": len(b"hello"),
    }
    assert calls[0]["files"]["file"] == ("renamed.txt", b"hello", "text/plain")
    assert download_path.read_bytes() == b"download-bytes"


def test_drive_write_shortcuts_build_requests(monkeypatch: Any, capsys: Any) -> None:
    calls: list[dict[str, Any]] = []

    def _fake_request_json(
        _self: FeishuClient,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        calls.append({"method": method, "path": path, "payload": payload, "params": params})
        if path == "/drive/v1/files/create_folder":
            return {"code": 0, "data": {"token": "fld_new", "url": "https://example.com/fld_new"}}
        if path == "/drive/v1/files/create_shortcut":
            return {"code": 0, "data": {"succ_shortcut_node": {"token": "shortcut_1"}}}
        if method == "DELETE":
            return {"code": 0, "data": {}}
        if path == "/drive/v1/permissions/doc_1/members/apply":
            return {"code": 0, "data": {"request_id": "req_1"}}
        if path == "/drive/v1/files/doc_1/new_comments":
            return {"code": 0, "data": {"comment_id": "c_1"}}
        raise AssertionError(f"unexpected path: {path}")

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)
    base = ["--as", "user", "--user-access-token", "user_token", "--format", "json"]

    assert cli.main(["drive", "+create-folder", *base, "--name", "Plans", "--folder-token", "fld_parent"]) == 0
    capsys.readouterr()
    assert cli.main(["drive", "+create-shortcut", *base, "--file-token", "doc_1", "--type", "docx", "--folder-token", "fld_parent"]) == 0
    capsys.readouterr()
    assert cli.main(["drive", "+delete", *base, "--file-token", "doc_1", "--type", "docx", "--yes"]) == 0
    capsys.readouterr()
    assert cli.main(["drive", "+apply-permission", *base, "--token", "doc_1", "--type", "docx", "--perm", "view", "--remark", "Need access"]) == 0
    capsys.readouterr()
    assert cli.main(["drive", "+add-comment", *base, "--doc", "doc_1", "--type", "docx", "--content", '[{"type":"text","text":"Looks good"}]', "--full-comment"]) == 0

    assert calls[0] == {
        "method": "POST",
        "path": "/drive/v1/files/create_folder",
        "payload": {"name": "Plans", "folder_token": "fld_parent"},
        "params": None,
    }
    assert calls[1]["payload"] == {
        "parent_token": "fld_parent",
        "refer_entity": {"refer_token": "doc_1", "refer_type": "docx"},
    }
    assert calls[2] == {
        "method": "DELETE",
        "path": "/drive/v1/files/doc_1",
        "payload": None,
        "params": {"type": "docx"},
    }
    assert calls[3] == {
        "method": "POST",
        "path": "/drive/v1/permissions/doc_1/members/apply",
        "payload": {"perm": "view", "remark": "Need access"},
        "params": {"type": "docx"},
    }
    assert calls[4]["path"] == "/drive/v1/files/doc_1/new_comments"
    assert calls[4]["payload"]["reply_elements"] == [{"type": "text", "text": "Looks good"}]


def test_drive_search_and_export_download(monkeypatch: Any, tmp_path: Any, capsys: Any) -> None:
    calls: list[dict[str, Any]] = []

    def _fake_request_json(
        _self: FeishuClient,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        calls.append({"method": method, "path": path, "payload": payload, "params": params})
        return {"code": 0, "data": {"res_units": [{"title": "Plan"}], "has_more": False}}

    class _FakeResponse:
        status_code = 200
        content = b"export-bytes"
        text = ""
        headers = {"content-type": "application/pdf"}

        def raise_for_status(self) -> None:
            return None

    class _FakeClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            return None

        def __enter__(self) -> "_FakeClient":
            return self

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
            return False

        def get(self, url: str, headers: dict[str, str] | None = None) -> _FakeResponse:
            assert "drive/v1/export_tasks/file/file_export/download" in url
            return _FakeResponse()

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)
    monkeypatch.setattr("feishu_bot_sdk.cli.commands.drive_shortcuts.httpx.Client", _FakeClient)

    base = ["--as", "user", "--user-access-token", "user_token", "--format", "json"]
    assert cli.main(["drive", "+search", *base, "--query", "roadmap", "--doc-types", "docx,sheet", "--page-size", "10"]) == 0
    capsys.readouterr()
    assert cli.main(["drive", "+export-download", *base, "--file-token", "file_export", "--file-name", "roadmap.pdf", "--output-dir", str(tmp_path)]) == 0

    assert calls[0]["method"] == "POST"
    assert calls[0]["path"] == "/search/v2/doc_wiki/search"
    assert calls[0]["payload"]["query"] == "roadmap"
    assert calls[0]["payload"]["page_size"] == 10
    assert calls[0]["payload"]["doc_filter"]["doc_types"] == ["DOCX", "SHEET"]
    assert (tmp_path / "roadmap.pdf").read_bytes() == b"export-bytes"


def test_drive_export_download_http_error_is_not_internal_error(monkeypatch: Any, tmp_path: Any, capsys: Any) -> None:
    class _FakeResponse:
        status_code = 404
        content = b"not found"
        text = '{"code":1061002,"msg":"not found"}'
        headers = {"content-type": "application/json"}

    class _FakeClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            return None

        def __enter__(self) -> "_FakeClient":
            return self

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
            return False

        def get(self, url: str, headers: dict[str, str] | None = None) -> _FakeResponse:
            assert "drive/v1/export_tasks/file/missing/download" in url
            return _FakeResponse()

    monkeypatch.setattr("feishu_bot_sdk.cli.commands.drive_shortcuts.httpx.Client", _FakeClient)

    code = cli.main(
        [
            "drive",
            "+export-download",
            "--as",
            "user",
            "--user-access-token",
            "user_token",
            "--file-token",
            "missing",
            "--output-dir",
            str(tmp_path),
            "--format",
            "json",
        ]
    )

    assert code == 4
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"]["type"] == "http_error"
    assert payload["error"]["code"] == 1061002
