from __future__ import annotations

import argparse
import mimetypes
import re
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import unquote

import httpx

from ...minutes import MinutesService
from ..runtime import _build_client


_FILENAME_STAR_RE = re.compile(r"filename\*=UTF-8''([^;]+)")
_FILENAME_RE = re.compile(r'filename="([^"]+)"|filename=([^;]+)')


def _parse_minute_tokens(value: Any) -> list[str]:
    tokens = [item.strip() for item in str(value or "").split(",") if item.strip()]
    if not tokens:
        raise ValueError("--minute-tokens is required")
    if len(tokens) > 50:
        raise ValueError("--minute-tokens supports up to 50 minute tokens per call")
    return tokens


def _safe_filename(name: str) -> str:
    cleaned = "".join("_" if char in '/\\\0' else char for char in name).strip()
    return cleaned or "minute.media"


def _download_filename(response: httpx.Response, minute_token: str) -> str:
    content_disposition = response.headers.get("content-disposition", "")
    star_match = _FILENAME_STAR_RE.search(content_disposition)
    if star_match:
        return _safe_filename(unquote(star_match.group(1)))

    match = _FILENAME_RE.search(content_disposition)
    if match:
        filename = match.group(1) or match.group(2) or ""
        if filename:
            return _safe_filename(filename.strip())

    path_name = Path(str(response.url.path or "")).name
    if path_name:
        return _safe_filename(path_name)

    content_type = response.headers.get("content-type", "").split(";", 1)[0].strip()
    suffix = mimetypes.guess_extension(content_type) or ".media"
    return _safe_filename(f"{minute_token}{suffix}")


def _resolve_output_path(*, output: Any, filename: str, single: bool) -> Path:
    output_value = str(output or "").strip()
    if single and output_value:
        target = Path(output_value)
        if target.exists() and target.is_dir():
            return target / filename
        return target

    output_dir = Path(output_value) if output_value else Path(".")
    return output_dir / filename


def _download_media_to_path(
    download_url: str,
    minute_token: str,
    *,
    output: Any,
    overwrite: bool,
    single: bool,
    timeout_seconds: float | None,
) -> tuple[Path, int]:
    with httpx.Client(follow_redirects=True, timeout=timeout_seconds) as client:
        response = client.get(download_url)
    response.raise_for_status()

    target = _resolve_output_path(
        output=output,
        filename=_download_filename(response, minute_token),
        single=single,
    )
    if target.exists() and not overwrite:
        raise ValueError(f"output file already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(response.content)
    return target, len(response.content)


def _extract_download_url(payload: Mapping[str, Any]) -> str:
    value = payload.get("download_url")
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise ValueError("minute media response does not contain download_url")


def _cmd_minutes_download(args: argparse.Namespace) -> Mapping[str, Any]:
    client = _build_client(args)
    service = MinutesService(client)
    tokens = _parse_minute_tokens(getattr(args, "minute_tokens", None))
    url_only = bool(getattr(args, "url_only", False))
    overwrite = bool(getattr(args, "overwrite", False))
    single = len(tokens) == 1

    downloads: list[dict[str, Any]] = []
    for token in tokens:
        item: dict[str, Any] = {"minute_token": token}
        try:
            media_info = service.get_minute_media_download_url(token)
            download_url = _extract_download_url(media_info)
            if url_only:
                item["download_url"] = download_url
            else:
                output_path, size_bytes = _download_media_to_path(
                    download_url,
                    token,
                    output=getattr(args, "output", None),
                    overwrite=overwrite,
                    single=single,
                    timeout_seconds=getattr(client.config, "timeout_seconds", None),
                )
                item["saved_path"] = str(output_path)
                item["size_bytes"] = size_bytes
        except Exception as exc:
            item["error"] = str(exc)
        downloads.append(item)

    if single:
        result = downloads[0]
        if "error" in result:
            raise ValueError(result["error"])
        return result

    success_count = sum(1 for item in downloads if "error" not in item)
    return {
        "downloads": downloads,
        "count": len(downloads),
        "success_count": success_count,
        "failure_count": len(downloads) - success_count,
    }


__all__ = ["_cmd_minutes_download"]
