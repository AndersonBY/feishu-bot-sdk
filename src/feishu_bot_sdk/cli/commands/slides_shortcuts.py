from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import quote

from ..runtime import _build_client, infer_mime_type, read_value


def _data(response: Mapping[str, Any]) -> dict[str, Any]:
    payload = response.get("data")
    if isinstance(payload, Mapping):
        return {str(key): value for key, value in payload.items()}
    return {}


def _presentation_xml(title: str) -> str:
    safe_title = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"<presentation><title>{safe_title}</title></presentation>"


def _json_array(value: Any) -> list[Any]:
    text = str(value or "").strip()
    if not text:
        return []
    parsed = json.loads(read_value(text))
    if not isinstance(parsed, list):
        raise ValueError("expected a JSON array")
    return parsed


def _media_upload(client: Any, file_path: str, presentation_id: str) -> dict[str, Any]:
    content = Path(file_path).read_bytes()
    file_name = os.path.basename(file_path)
    return _data(
        client.request_multipart(
            "POST",
            "/drive/v1/medias/upload_all",
            data={
                "file_name": file_name,
                "parent_type": "slide_file",
                "parent_node": presentation_id,
                "size": len(content),
            },
            files={"file": (file_name, content, infer_mime_type(file_path))},
        )
    )


def _cmd_slides_shortcut(args: argparse.Namespace) -> Mapping[str, Any]:
    command = str(getattr(args, "slides_command", "") or "").strip()
    client = _build_client(args)

    if command == "create":
        title = str(getattr(args, "title", "") or "Untitled presentation")
        data = _data(
            client.request_json(
                "POST",
                "/slides_ai/v1/xml_presentations",
                payload={"xml_presentation": {"content": _presentation_xml(title)}},
            )
        )
        presentation_id = str(data.get("xml_presentation_id") or "")
        slide_ids: list[str] = []
        for item in _json_array(getattr(args, "slides", None)):
            slide_data = _data(
                client.request_json(
                    "POST",
                    f"/slides_ai/v1/xml_presentations/{quote(presentation_id, safe='')}/slide",
                    params={"revision_id": -1},
                    payload={"slide": {"content": str(item)}},
                )
            )
            slide_id = str(slide_data.get("slide_id") or "")
            if slide_id:
                slide_ids.append(slide_id)
        return {
            "xml_presentation_id": presentation_id,
            "title": title,
            "revision_id": data.get("revision_id"),
            "slide_ids": slide_ids,
            "slides_added": len(slide_ids),
        }

    if command == "media-upload":
        presentation_id = str(getattr(args, "presentation", "") or "").strip()
        file_path = str(getattr(args, "file", "") or "").strip()
        if not presentation_id or not file_path:
            raise ValueError("specify --presentation and --file")
        upload = _media_upload(client, file_path, presentation_id)
        return {
            "file_token": upload.get("file_token"),
            "file_name": os.path.basename(file_path),
            "presentation_id": presentation_id,
        }

    if command == "replace-slide":
        presentation_id = str(getattr(args, "presentation", "") or "").strip()
        slide_id = str(getattr(args, "slide_id", "") or "").strip()
        if not presentation_id or not slide_id:
            raise ValueError("specify --presentation and --slide-id")
        parts = _json_array(getattr(args, "parts", None))
        revision_id = int(getattr(args, "revision_id", -1) or -1)
        params: dict[str, Any] = {"slide_id": slide_id, "revision_id": revision_id}
        tid = str(getattr(args, "tid", "") or "").strip()
        if tid:
            params["tid"] = tid
        data = _data(
            client.request_json(
                "POST",
                f"/slides_ai/v1/xml_presentations/{quote(presentation_id, safe='')}/slide/replace",
                params=params,
                payload={"parts": parts},
            )
        )
        return {"xml_presentation_id": presentation_id, "slide_id": slide_id, "parts_count": len(parts), **data}

    raise ValueError(f"unsupported slides shortcut: {command}")


__all__ = ["_cmd_slides_shortcut"]
