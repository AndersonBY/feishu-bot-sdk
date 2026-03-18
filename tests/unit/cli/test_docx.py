import json
from pathlib import Path
from typing import Any
from feishu_bot_sdk import cli


def test_docx_get_content_json_output(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    monkeypatch.setattr(
        "feishu_bot_sdk.docx.DocContentService.get_content",
        lambda _self, doc_token, doc_type="docx", content_type="markdown", lang=None: {
            "content": f"{doc_token}:{doc_type}:{content_type}:{lang}"
        },
    )

    code = cli.main(
        [
            "docx",
            "get-content",
            "--doc-token",
            "doccn_xxx",
            "--format",
            "json",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["content"] == "doccn_xxx:docx:markdown:None"


def test_docx_get_content_writes_output(
    monkeypatch: Any, tmp_path: Path, capsys: Any
) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    monkeypatch.setattr(
        "feishu_bot_sdk.docx.DocContentService.get_content",
        lambda _self, doc_token, doc_type="docx", content_type="markdown", lang=None: {
            "content": "# hello"
        },
    )

    output = tmp_path / "report.md"
    code = cli.main(
        [
            "docx",
            "get-content",
            "--doc-token",
            "doccn_xxx",
            "--output",
            str(output),
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert output.read_text(encoding="utf-8") == "# hello"
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["output"] == str(output)


def test_docx_insert_content_from_file(
    monkeypatch: Any, tmp_path: Path, capsys: Any
) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    captured: dict[str, Any] = {}

    def _fake_insert_content(
        _self: Any,
        document_id: str,
        content: str,
        *,
        block_id: str | None = None,
        content_type: str = "markdown",
        index: int = -1,
        document_revision_id: int | None = None,
        client_token: str | None = None,
        user_id_type: str | None = None,
    ) -> dict[str, Any]:
        captured["document_id"] = document_id
        captured["content"] = content
        captured["block_id"] = block_id
        captured["content_type"] = content_type
        captured["index"] = index
        captured["document_revision_id"] = document_revision_id
        captured["client_token"] = client_token
        captured["user_id_type"] = user_id_type
        return {
            "document_id": document_id,
            "block_id": block_id,
            "content_type": content_type,
            "batch_count": 1,
            "converted": {
                "first_level_block_ids": ["tmp_1"],
                "blocks": [{"block_id": "tmp_1"}, {"block_id": "tmp_2"}],
            },
            "inserted_batches": [
                {
                    "block_id_relations": [
                        {"temporary_block_id": "tmp_1", "block_id": "blk_1"},
                        {"temporary_block_id": "tmp_2", "block_id": "blk_2"},
                    ]
                }
            ],
            "image_replacements": [],
        }

    monkeypatch.setattr(
        "feishu_bot_sdk.docx.DocxService.insert_content", _fake_insert_content
    )

    content_file = tmp_path / "content.md"
    content_file.write_text("## hi", encoding="utf-8")

    code = cli.main(
        [
            "docx",
            "insert-content",
            "--document-id",
            "doc_1",
            "--block-id",
            "blk_1",
            "--content-file",
            str(content_file),
            "--document-revision-id",
            "-1",
            "--client-token",
            "ct_1",
            "--user-id-type",
            "open_id",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert captured == {
        "document_id": "doc_1",
        "content": "## hi",
        "block_id": "blk_1",
        "content_type": "markdown",
        "index": -1,
        "document_revision_id": -1,
        "client_token": "ct_1",
        "user_id_type": "open_id",
    }
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["document_id"] == "doc_1"
    assert payload["block_id"] == "blk_1"
    assert payload["content_type"] == "markdown"
    assert payload["input_char_count"] == 5
    assert payload["batch_count"] == 1
    assert payload["first_level_block_count"] == 1
    assert payload["converted_block_count"] == 2
    assert payload["inserted_block_count"] == 2
    assert payload["image_replacement_count"] == 0
    assert "converted" not in payload
    assert "inserted_batches" not in payload


def test_docx_insert_content_full_response(
    monkeypatch: Any, tmp_path: Path, capsys: Any
) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    response = {
        "document_id": "doc_1",
        "block_id": "doc_1",
        "content_type": "markdown",
        "batch_count": 1,
        "converted": {
            "first_level_block_ids": ["tmp_1"],
            "blocks": [{"block_id": "tmp_1"}],
        },
        "inserted_batches": [
            {"block_id_relations": [{"temporary_block_id": "tmp_1", "block_id": "blk_1"}]}
        ],
        "image_replacements": [],
    }

    monkeypatch.setattr(
        "feishu_bot_sdk.docx.DocxService.insert_content", lambda *_args, **_kwargs: response
    )

    content_file = tmp_path / "content.md"
    content_file.write_text("## hi", encoding="utf-8")

    code = cli.main(
        [
            "docx",
            "insert-content",
            "--document-id",
            "doc_1",
            "--content-file",
            str(content_file),
            "--full-response",
            "--format",
            "json",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == response


def test_docx_list_blocks_all(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    calls: list[str | None] = []

    def _fake_list_blocks(
        _self: Any,
        document_id: str,
        *,
        page_size: int | None = None,
        page_token: str | None = None,
        document_revision_id: int | None = None,
        user_id_type: str | None = None,
    ) -> dict[str, Any]:
        assert document_id == "doc_1"
        calls.append(page_token)
        if page_token == "next_1":
            return {"items": [{"block_id": "b2"}], "has_more": False}
        return {"items": [{"block_id": "b1"}], "has_more": True, "page_token": "next_1"}

    monkeypatch.setattr(
        "feishu_bot_sdk.docx.DocxDocumentService.list_blocks", _fake_list_blocks
    )

    code = cli.main(
        ["docx", "list-blocks", "--document-id", "doc_1", "--all", "--format", "json"]
    )
    assert code == 0
    assert calls == [None, "next_1"]
    payload = json.loads(capsys.readouterr().out)
    assert payload["all"] is True
    assert payload["count"] == 2
    assert [item["block_id"] for item in payload["items"]] == ["b1", "b2"]


def test_docx_get_content_rejects_invalid_doc_type(capsys: Any) -> None:
    code = cli.main(
        [
            "docx",
            "get-content",
            "--doc-token",
            "doccn_xxx",
            "--doc-type",
            "invalid_doc_type",
        ]
    )
    assert code == 2
    assert "invalid choice" in capsys.readouterr().err
