from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import quote

from ..runtime import _build_client, read_value


_FORMAT_SYNTAX_TYPE = {"plantuml": 1, "mermaid": 2}


def _data(response: Mapping[str, Any]) -> dict[str, Any]:
    payload = response.get("data")
    if isinstance(payload, Mapping):
        return {str(key): value for key, value in payload.items()}
    return {}


def _source_text(value: Any) -> str:
    text = str(value or "")
    if not text:
        raise ValueError("specify --source")
    return read_value(text)


def _cmd_whiteboard_query(args: argparse.Namespace) -> Mapping[str, Any]:
    token = str(getattr(args, "whiteboard_token", "") or "").strip()
    if not token:
        raise ValueError("specify --whiteboard-token")
    output_as = str(getattr(args, "output_as", "") or "raw").strip().lower()
    client = _build_client(args)
    if output_as == "image":
        from .docs_shortcuts import _download_openapi_bytes

        output = str(getattr(args, "output", "") or "").strip()
        if not output:
            raise ValueError("--output is required when --output-as image")
        content, headers = _download_openapi_bytes(client, f"/board/v1/whiteboards/{quote(token, safe='')}/download_as_image")
        target = Path(output)
        target.mkdir(parents=True, exist_ok=True)
        path = target / f"{token}.png"
        path.write_bytes(content)
        return {"preview_image_path": str(path), "size_bytes": len(content), "content_type": headers.get("content-type")}
    data = _data(client.request_json("GET", f"/board/v1/whiteboards/{quote(token, safe='')}/nodes"))
    nodes = data.get("nodes") if isinstance(data.get("nodes"), list) else []
    if output_as == "raw":
        return {"nodes": nodes}
    return {"nodes": nodes, "code_blocks": []}


def _cmd_whiteboard_update(args: argparse.Namespace) -> Mapping[str, Any]:
    token = str(getattr(args, "whiteboard_token", "") or "").strip()
    if not token:
        raise ValueError("specify --whiteboard-token")
    input_format = str(getattr(args, "input_format", "") or "raw").strip().lower()
    overwrite = bool(getattr(args, "overwrite", False))
    idempotent_token = str(getattr(args, "idempotent_token", "") or "").strip()
    source = _source_text(getattr(args, "source", ""))
    client = _build_client(args)
    params = {"client_token": idempotent_token} if idempotent_token else None
    if input_format in _FORMAT_SYNTAX_TYPE:
        data = _data(
            client.request_json(
                "POST",
                f"/board/v1/whiteboards/{quote(token, safe='')}/nodes/plantuml",
                params=params,
                payload={
                    "plant_uml_code": source,
                    "syntax_type": _FORMAT_SYNTAX_TYPE[input_format],
                    "parse_mode": 1,
                    "diagram_type": 0,
                    "overwrite": overwrite,
                },
            )
        )
        return {"created_node_id": data.get("node_id")}
    try:
        parsed = json.loads(source)
    except json.JSONDecodeError as exc:
        raise ValueError("--source must be JSON when --input-format raw") from exc
    nodes = parsed.get("raw_nodes") if isinstance(parsed, Mapping) else None
    if nodes is None and isinstance(parsed, Mapping):
        data = parsed.get("data")
        if isinstance(data, Mapping):
            result = data.get("result")
            if isinstance(result, Mapping):
                nodes = result.get("nodes")
    if nodes is None:
        nodes = parsed if isinstance(parsed, list) else []
    data = _data(
        client.request_json(
            "POST",
            f"/board/v1/whiteboards/{quote(token, safe='')}/nodes",
            params=params,
            payload={"nodes": nodes, "overwrite": overwrite},
        )
    )
    return {"created_node_ids": data.get("ids"), "idempotent_token": data.get("client_token")}


__all__ = ["_cmd_whiteboard_query", "_cmd_whiteboard_update"]
