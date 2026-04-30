from __future__ import annotations

import json
from typing import Any

import feishu_bot_sdk.cli as cli
from feishu_bot_sdk.feishu import FeishuClient


def test_docs_help_lists_lark_shortcuts(capsys: Any) -> None:
    code = cli.main(["docs", "--help"])

    assert code == 0
    output = capsys.readouterr().out
    for command in (
        "+search",
        "+create",
        "+fetch",
        "+update",
        "+media-insert",
        "+media-upload",
        "+media-preview",
        "+media-download",
        "+whiteboard-update",
    ):
        assert command in output


def test_docs_create_fetch_update_and_search(monkeypatch: Any, tmp_path: Any, capsys: Any) -> None:
    calls: list[dict[str, Any]] = []
    source = tmp_path / "README.md"
    source.write_text("# VectorVein\n", encoding="utf-8")

    def _fake_request_json(
        _self: FeishuClient,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        calls.append({"method": method, "path": path, "payload": payload, "params": params})
        if path == "/docs_ai/v1/documents":
            return {"code": 0, "data": {"document": {"document_id": "docx_1", "url": "https://example.com/docx_1"}}}
        if path == "/docs_ai/v1/documents/docx_1/fetch":
            return {"code": 0, "data": {"document": {"content": "# Title"}}}
        if path == "/docs_ai/v1/documents/docx_1":
            return {"code": 0, "data": {"document": {"document_id": "docx_1"}}}
        if path == "/search/v2/doc_wiki/search":
            return {"code": 0, "data": {"res_units": [{"title": "Title"}], "has_more": False}}
        raise AssertionError(f"unexpected path: {path}")

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)
    base = ["--as", "user", "--user-access-token", "user_token", "--format", "json"]

    assert cli.main(["docs", "+create", *base, "--content", f"@{source}", "--doc-format", "markdown", "--parent-token", "fld_1"]) == 0
    capsys.readouterr()
    assert cli.main(["docs", "+fetch", *base, "--doc", "docx_1", "--doc-format", "markdown", "--detail", "simple"]) == 0
    capsys.readouterr()
    assert cli.main(["docs", "+update", *base, "--doc", "docx_1", "--command", "append", "--content", "hello", "--doc-format", "markdown"]) == 0
    capsys.readouterr()
    assert cli.main(["docs", "+search", *base, "--query", "Title", "--filter", '{"folder_tokens":["fld_1"]}', "--page-size", "10"]) == 0

    assert calls[0] == {
        "method": "POST",
        "path": "/docs_ai/v1/documents",
        "payload": {
            "format": "markdown",
            "content": "# VectorVein\n",
            "parent_token": "fld_1",
        },
        "params": None,
    }
    assert calls[1]["method"] == "POST"
    assert calls[1]["path"] == "/docs_ai/v1/documents/docx_1/fetch"
    assert calls[1]["payload"]["format"] == "markdown"
    assert calls[2]["method"] == "PUT"
    assert calls[2]["path"] == "/docs_ai/v1/documents/docx_1"
    assert calls[2]["payload"]["command"] == "block_insert_after"
    assert calls[2]["payload"]["block_id"] == "-1"
    assert calls[3]["path"] == "/search/v2/doc_wiki/search"
    assert calls[3]["payload"]["doc_filter"] == {"folder_tokens": ["fld_1"]}
    assert calls[3]["payload"]["wiki_filter"] == {}


def test_docs_media_upload_insert_and_download(monkeypatch: Any, tmp_path: Any, capsys: Any) -> None:
    media_path = tmp_path / "image.png"
    media_path.write_bytes(b"png-bytes")
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
        if path == "/docx/v1/documents/docx_1/blocks/docx_1":
            return {"code": 0, "data": {"block": {"children": []}}}
        if path == "/docx/v1/documents/docx_1/blocks/docx_1/children":
            return {"code": 0, "data": {"children": [{"block_id": "block_new"}]}}
        if path == "/docx/v1/documents/docx_1/blocks/batch_update":
            return {"code": 0, "data": {"blocks": [{"block_id": "block_new"}]}}
        return {"code": 0, "data": {}}

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
        return {"code": 0, "data": {"file_token": "media_1"}}

    class _FakeResponse:
        status_code = 200
        content = b"downloaded"
        text = ""
        headers = {"content-type": "image/png"}

        def raise_for_status(self) -> None:
            return None

    class _FakeClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            return None

        def __enter__(self) -> "_FakeClient":
            return self

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
            return False

        def get(self, url: str, headers: dict[str, str] | None = None, params: dict[str, str] | None = None) -> _FakeResponse:
            assert "/drive/v1/medias/media_1" in url or "/drive/v1/medias/media_preview" in url
            return _FakeResponse()

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)
    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_multipart", _fake_request_multipart)
    monkeypatch.setattr("feishu_bot_sdk.cli.commands.docs_shortcuts.httpx.Client", _FakeClient)

    base = ["--as", "bot", "--access-token", "tenant_token", "--format", "json"]
    assert cli.main(["docs", "+media-upload", *base, "--file", str(media_path), "--parent-type", "docx_image", "--parent-node", "block_1", "--doc-id", "docx_1"]) == 0
    capsys.readouterr()
    assert cli.main(["docs", "+media-insert", *base, "--file", str(media_path), "--doc", "docx_1", "--type", "image", "--caption", "A chart"]) == 0
    capsys.readouterr()
    output_path = tmp_path / "media.png"
    assert cli.main(["docs", "+media-download", *base, "--token", "media_1", "--output", str(output_path)]) == 0
    capsys.readouterr()
    preview_path = tmp_path / "preview.png"
    assert cli.main(["docs", "+media-preview", *base, "--token", "media_preview", "--output", str(preview_path)]) == 0

    assert calls[0]["path"] == "/drive/v1/medias/upload_all"
    assert calls[0]["data"]["parent_type"] == "docx_image"
    assert calls[1]["path"] == "/docx/v1/documents/docx_1/blocks/docx_1"
    assert calls[2]["path"] == "/docx/v1/documents/docx_1/blocks/docx_1/children"
    assert calls[3]["path"] == "/drive/v1/medias/upload_all"
    assert calls[4]["path"] == "/docx/v1/documents/docx_1/blocks/batch_update"
    assert output_path.read_bytes() == b"downloaded"
    assert preview_path.read_bytes() == b"downloaded"


def test_docs_media_download_http_error_is_not_internal_error(monkeypatch: Any, tmp_path: Any, capsys: Any) -> None:
    class _FakeResponse:
        status_code = 404
        content = b"not found"
        text = '{"code":1770001,"msg":"not found"}'
        headers = {"content-type": "application/json"}

    class _FakeClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            return None

        def __enter__(self) -> "_FakeClient":
            return self

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
            return False

        def get(self, url: str, headers: dict[str, str] | None = None, params: dict[str, str] | None = None) -> _FakeResponse:
            assert "/drive/v1/medias/missing/download" in url
            return _FakeResponse()

    monkeypatch.setattr("feishu_bot_sdk.cli.commands.docs_shortcuts.httpx.Client", _FakeClient)

    code = cli.main(
        [
            "docs",
            "+media-download",
            "--as",
            "bot",
            "--access-token",
            "tenant_token",
            "--token",
            "missing",
            "--output",
            str(tmp_path / "missing.bin"),
            "--format",
            "json",
        ]
    )

    assert code == 4
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"]["type"] == "http_error"
    assert payload["error"]["code"] == 1770001
