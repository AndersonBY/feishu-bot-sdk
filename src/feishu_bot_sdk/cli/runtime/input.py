from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping

def _resolve_text_input(
    *,
    text: str | None,
    file_path: str | None,
    stdin_enabled: bool = False,
    name: str,
) -> str:
    source_count = int(bool(text)) + int(bool(file_path)) + int(bool(stdin_enabled))
    if source_count != 1:
        raise ValueError(
            f"exactly one of --{name}, --{name}-file or --{name}-stdin is required"
        )
    if text is not None:
        return text
    if file_path is not None:
        return Path(str(file_path)).read_text(encoding="utf-8")
    return _read_stdin_text()


def _parse_json_object(
    *,
    json_text: str | None,
    file_path: str | None,
    stdin_enabled: bool = False,
    name: str,
    required: bool,
) -> dict[str, Any]:
    source_count = int(bool(json_text)) + int(bool(file_path)) + int(bool(stdin_enabled))
    if source_count > 1:
        raise ValueError(
            f"only one of --{name}-json, --{name}-file or --{name}-stdin can be used"
        )
    if source_count == 0:
        if required:
            raise ValueError(
                f"one of --{name}-json, --{name}-file or --{name}-stdin is required"
            )
        return {}

    if json_text is not None:
        raw = json_text
    elif file_path is not None:
        raw = Path(str(file_path)).read_text(encoding="utf-8")
    else:
        raw = _read_stdin_text()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{name} is not valid JSON: {exc}") from exc
    if not isinstance(parsed, Mapping):
        raise ValueError(f"{name} must be a JSON object")
    return {str(key): value for key, value in parsed.items()}


def _parse_json_array(
    *,
    json_text: str | None,
    file_path: str | None,
    stdin_enabled: bool = False,
    name: str,
    required: bool,
) -> list[Any]:
    source_count = int(bool(json_text)) + int(bool(file_path)) + int(bool(stdin_enabled))
    if source_count > 1:
        raise ValueError(
            f"only one of --{name}-json, --{name}-file or --{name}-stdin can be used"
        )
    if source_count == 0:
        if required:
            raise ValueError(
                f"one of --{name}-json, --{name}-file or --{name}-stdin is required"
            )
        return []

    if json_text is not None:
        raw = json_text
    elif file_path is not None:
        raw = Path(str(file_path)).read_text(encoding="utf-8")
    else:
        raw = _read_stdin_text()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{name} is not valid JSON: {exc}") from exc
    if not isinstance(parsed, list):
        raise ValueError(f"{name} must be a JSON array")
    return list(parsed)


def _resolve_raw_body(
    *,
    body_json: str | None,
    body_file: str | None,
    stdin_enabled: bool = False,
) -> bytes:
    source_count = int(bool(body_json)) + int(bool(body_file)) + int(bool(stdin_enabled))
    if source_count > 1:
        raise ValueError("only one of --body-json, --body-file or --body-stdin can be used")
    if source_count == 0:
        raise ValueError("one of --body-json, --body-file or --body-stdin is required")
    if body_json is not None:
        return body_json.encode("utf-8")
    if body_file is not None:
        return Path(str(body_file)).read_bytes()
    return _read_stdin_bytes()


def _read_stdin_text() -> str:
    return sys.stdin.read()


def _read_stdin_bytes() -> bytes:
    stream = getattr(sys.stdin, "buffer", None)
    if stream is None:
        return sys.stdin.read().encode("utf-8")
    data = stream.read()
    if isinstance(data, bytes):
        return data
    return bytes(data)


def _normalize_path(path: str) -> str:
    if path.startswith("/"):
        return path
    return f"/{path}"


def _read_request_body(headers: Any, stream: Any) -> bytes:
    content_length_raw = None
    items = headers.items() if hasattr(headers, "items") else []
    for key, value in items:
        if str(key).lower() == "content-length":
            content_length_raw = value
            break
    if content_length_raw is None:
        return b""
    try:
        content_length = int(str(content_length_raw))
    except ValueError:
        return b""
    if content_length <= 0:
        return b""
    return bytes(stream.read(content_length))


__all__ = [name for name in globals() if not name.startswith("__")]
