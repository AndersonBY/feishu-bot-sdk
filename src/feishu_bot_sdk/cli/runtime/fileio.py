from __future__ import annotations

import mimetypes
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, TextIO


@dataclass
class LocalFileIO:
    stdin: TextIO | None = None
    stdin_buffer: BinaryIO | None = None

    def read_text(self, path: str | Path) -> str:
        return Path(path).read_text(encoding="utf-8")

    def read_bytes(self, path: str | Path) -> bytes:
        return Path(path).read_bytes()

    def read_stdin(self) -> str:
        stream = self.stdin if self.stdin is not None else sys.stdin
        return stream.read()

    def read_stdin_bytes(self) -> bytes:
        if self.stdin_buffer is not None:
            return self.stdin_buffer.read()
        stream = self.stdin if self.stdin is not None else sys.stdin
        buffer = getattr(stream, "buffer", None)
        if buffer is None:
            return stream.read().encode("utf-8")
        data = buffer.read()
        if isinstance(data, bytes):
            return data
        return bytes(data)


def read_value(
    value: str,
    *,
    fileio: LocalFileIO | None = None,
    allow_file: bool = True,
    allow_stdin: bool = True,
) -> str:
    io = fileio or LocalFileIO()
    if value == "-":
        if not allow_stdin:
            raise ValueError("stdin input is not enabled")
        return io.read_stdin()
    if value.startswith("@"):
        if not allow_file:
            raise ValueError("@path input is not enabled")
        path = value[1:]
        if not path:
            raise ValueError("@path input requires a file path")
        return io.read_text(path)
    return value


def resolve_output_path(
    path: str | Path,
    *,
    base_dir: str | Path | None = None,
    must_stay_under_base: bool = True,
) -> Path:
    raw = Path(path)
    base = Path.cwd() if base_dir is None else Path(base_dir)
    resolved = raw if raw.is_absolute() else base / raw
    normalized = resolved.resolve()
    if must_stay_under_base:
        base_normalized = base.resolve()
        if normalized != base_normalized and base_normalized not in normalized.parents:
            raise ValueError(f"output path must stay under {base_normalized}")
    return normalized


def infer_mime_type(path: str | Path, *, default: str = "application/octet-stream") -> str:
    mime_type, _ = mimetypes.guess_type(str(path))
    return mime_type or default


def parse_file_upload_value(value: str, *, default_field: str = "file") -> tuple[str, str]:
    text = str(value or "").strip()
    if not text:
        raise ValueError("--file requires a path")
    if "=" in text:
        field, path = text.split("=", 1)
        field = field.strip()
        path = path.strip()
        if not field:
            raise ValueError("--file field name is required")
        if not path:
            raise ValueError("--file path is required")
        return field, path
    return default_field, text


def build_multipart_file(
    value: str,
    *,
    default_field: str = "file",
    fileio: LocalFileIO | None = None,
) -> tuple[str, tuple[str, bytes, str], dict[str, str]]:
    field, raw_path = parse_file_upload_value(value, default_field=default_field)
    io = fileio or LocalFileIO()
    if raw_path == "-":
        filename = "stdin"
        data = io.read_stdin_bytes()
        mime_type = "application/octet-stream"
    else:
        path = Path(raw_path)
        filename = path.name or "file"
        data = io.read_bytes(path)
        mime_type = infer_mime_type(path)
    return field, (filename, data, mime_type), {
        "field": field,
        "path": raw_path,
        "mime_type": mime_type,
    }


__all__ = [name for name in globals() if not name.startswith("__")]
