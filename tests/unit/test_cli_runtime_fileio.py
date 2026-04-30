from __future__ import annotations

import io
from pathlib import Path

import pytest

from feishu_bot_sdk.cli.runtime.fileio import (
    LocalFileIO,
    infer_mime_type,
    read_value,
    resolve_output_path,
)


def test_read_value_supports_literal_file_reference_and_stdin(tmp_path: Path) -> None:
    payload = tmp_path / "payload.json"
    payload.write_text('{"ok":true}', encoding="utf-8")
    fileio = LocalFileIO(stdin=io.StringIO("from-stdin"))

    assert read_value("literal", fileio=fileio) == "literal"
    assert read_value(f"@{payload}", fileio=fileio) == '{"ok":true}'
    assert read_value("-", fileio=fileio) == "from-stdin"


def test_read_value_rejects_file_reference_when_file_input_is_disabled(tmp_path: Path) -> None:
    payload = tmp_path / "payload.json"
    payload.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="@path input is not enabled"):
        read_value(f"@{payload}", allow_file=False)


def test_resolve_output_path_blocks_parent_escape_when_requested(tmp_path: Path) -> None:
    assert resolve_output_path("nested/out.json", base_dir=tmp_path) == tmp_path / "nested" / "out.json"

    with pytest.raises(ValueError, match="must stay under"):
        resolve_output_path("../escape.json", base_dir=tmp_path)


def test_infer_mime_type_uses_known_type_and_default() -> None:
    assert infer_mime_type("report.png") == "image/png"
    assert infer_mime_type("archive.unknown-extension") == "application/octet-stream"

