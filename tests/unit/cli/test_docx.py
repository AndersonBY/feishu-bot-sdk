import json
from pathlib import Path
from typing import Any
from feishu_bot_sdk import cli


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
        content_base_dir: str | None = None,
    ) -> dict[str, Any]:
        captured["document_id"] = document_id
        captured["content"] = content
        captured["block_id"] = block_id
        captured["content_type"] = content_type
        captured["index"] = index
        captured["document_revision_id"] = document_revision_id
        captured["client_token"] = client_token
        captured["user_id_type"] = user_id_type
        captured["content_base_dir"] = content_base_dir
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
            "+insert-content",
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
    assert captured["document_id"] == "doc_1"
    assert captured["content"] == "## hi"
    assert captured["block_id"] == "blk_1"
    assert captured["content_type"] == "markdown"
    assert captured["index"] == -1
    assert str(captured["document_revision_id"]) == "-1"
    assert captured["client_token"] == "ct_1"
    assert captured["user_id_type"] == "open_id"
    assert captured["content_base_dir"] == str(content_file.resolve().parent)
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
            "+insert-content",
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
