from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import quote

import httpx

from ...exceptions import HTTPRequestError
from .whiteboard_shortcuts import _cmd_whiteboard_update
from ..runtime import _build_client, infer_mime_type, read_value


def _data(response: Mapping[str, Any]) -> dict[str, Any]:
    payload = response.get("data")
    if isinstance(payload, Mapping):
        return {str(key): value for key, value in payload.items()}
    return {}


def _download_openapi_bytes(client: Any, path: str, *, params: dict[str, Any] | None = None) -> tuple[bytes, Mapping[str, str]]:
    base_url = str(getattr(client.config, "base_url", "") or "https://open.feishu.cn/open-apis").rstrip("/")
    url = f"{base_url}{path}"
    headers = {"Authorization": f"Bearer {_download_bearer_token(client)}"}
    request_kwargs: dict[str, Any] = {"headers": headers}
    if params is not None:
        request_kwargs["params"] = params
    with httpx.Client(timeout=getattr(client.config, "timeout_seconds", 30.0)) as http_client:
        try:
            response = http_client.get(url, **request_kwargs)
        except httpx.TimeoutException as exc:
            raise HTTPRequestError(f"http request timed out: {exc}") from exc
        except httpx.RequestError as exc:
            raise HTTPRequestError(f"http request failed: {exc}") from exc
    if response.status_code >= 400:
        raise HTTPRequestError(
            f"http request failed: {response.status_code}",
            status_code=response.status_code,
            response_text=response.text,
            response_headers=dict(response.headers),
        )
    return response.content, response.headers


def _download_bearer_token(client: Any) -> str:
    config = getattr(client, "config", None)
    for field in ("access_token", "user_access_token", "app_access_token"):
        token = getattr(config, field, None)
        if token:
            return str(token)
    return str(client.get_access_token())


def _document_token(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError("specify --doc")
    return text.rstrip("/").split("/")[-1]


def _content_value(value: Any) -> str:
    text = str(value or "")
    if not text:
        raise ValueError("specify --content")
    return read_value(text)


def _cmd_docs_create(args: argparse.Namespace) -> Mapping[str, Any]:
    body: dict[str, Any] = {
        "format": str(getattr(args, "doc_format", "") or "xml"),
        "content": _content_value(getattr(args, "content", "")),
    }
    parent_token = str(getattr(args, "parent_token", "") or "").strip()
    if parent_token:
        body["parent_token"] = parent_token
    parent_position = str(getattr(args, "parent_position", "") or "").strip()
    if parent_position:
        body["parent_position"] = parent_position
    client = _build_client(args)
    return _data(client.request_json("POST", "/docs_ai/v1/documents", payload=body))


def _cmd_docs_fetch(args: argparse.Namespace) -> Mapping[str, Any]:
    doc = _document_token(getattr(args, "doc", ""))
    body: dict[str, Any] = {"format": str(getattr(args, "doc_format", "") or "xml")}
    detail = str(getattr(args, "detail", "") or "simple")
    if detail == "with-ids":
        body["export_option"] = {"export_block_id": True}
    elif detail == "full":
        body["export_option"] = {
            "export_block_id": True,
            "export_style_attrs": True,
            "export_cite_extra_data": True,
        }
    else:
        body["export_option"] = {
            "export_block_id": False,
            "export_style_attrs": False,
            "export_cite_extra_data": False,
        }
    client = _build_client(args)
    return _data(client.request_json("POST", f"/docs_ai/v1/documents/{quote(doc, safe='')}/fetch", payload=body))


def _cmd_docs_update(args: argparse.Namespace) -> Mapping[str, Any]:
    doc = _document_token(getattr(args, "doc", ""))
    command = str(getattr(args, "command", "") or "").strip()
    if command == "append":
        command = "block_insert_after"
        block_id = "-1"
    else:
        block_id = str(getattr(args, "block_id", "") or "").strip()
    if not command:
        raise ValueError("specify --command")
    body: dict[str, Any] = {
        "format": str(getattr(args, "doc_format", "") or "xml"),
        "command": command,
    }
    content = str(getattr(args, "content", "") or "")
    if content:
        body["content"] = read_value(content)
    pattern = str(getattr(args, "pattern", "") or "").strip()
    if pattern:
        body["pattern"] = pattern
    if block_id:
        body["block_id"] = block_id
    src_block_ids = str(getattr(args, "src_block_ids", "") or "").strip()
    if src_block_ids:
        body["src_block_ids"] = src_block_ids
    client = _build_client(args)
    return _data(client.request_json("PUT", f"/docs_ai/v1/documents/{quote(doc, safe='')}", payload=body))


def _cmd_docs_search(args: argparse.Namespace) -> Mapping[str, Any]:
    body: dict[str, Any] = {
        "query": str(getattr(args, "query", "") or ""),
        "page_size": int(getattr(args, "page_size", 15) or 15),
    }
    page_token = str(getattr(args, "page_token", "") or "").strip()
    if page_token:
        body["page_token"] = page_token
    filter_text = str(getattr(args, "filter", "") or "").strip()
    if filter_text:
        try:
            filter_payload = json.loads(filter_text)
        except json.JSONDecodeError as exc:
            raise ValueError("--filter is not valid JSON") from exc
        if not isinstance(filter_payload, Mapping):
            raise ValueError("--filter must be a JSON object")
        body["doc_filter"] = {str(key): value for key, value in filter_payload.items() if key != "space_ids"}
        body["wiki_filter"] = {str(key): value for key, value in filter_payload.items() if key != "folder_tokens"}
    else:
        body["doc_filter"] = {}
        body["wiki_filter"] = {}
    client = _build_client(args)
    data = _data(client.request_json("POST", "/search/v2/doc_wiki/search", payload=body))
    return {
        "total": data.get("total"),
        "has_more": data.get("has_more"),
        "page_token": data.get("page_token"),
        "results": data.get("res_units") if isinstance(data.get("res_units"), list) else [],
    }


def _media_upload(client: Any, file_path: str, *, parent_type: str, parent_node: str, doc_id: str = "") -> dict[str, Any]:
    content = Path(file_path).read_bytes()
    file_name = os.path.basename(file_path)
    data: dict[str, object] = {
        "file_name": file_name,
        "parent_type": parent_type,
        "parent_node": parent_node,
        "size": len(content),
    }
    if doc_id:
        data["extra"] = json.dumps({"drive_route_token": doc_id}, ensure_ascii=False)
    return _data(
        client.request_multipart(
            "POST",
            "/drive/v1/medias/upload_all",
            data=data,
            files={"file": (file_name, content, infer_mime_type(file_path))},
        )
    )


def _cmd_docs_media_upload(args: argparse.Namespace) -> Mapping[str, Any]:
    file_path = str(getattr(args, "file", "") or "").strip()
    parent_type = str(getattr(args, "parent_type", "") or "").strip()
    parent_node = str(getattr(args, "parent_node", "") or "").strip()
    if not file_path or not parent_type or not parent_node:
        raise ValueError("specify --file, --parent-type, and --parent-node")
    client = _build_client(args)
    data = _media_upload(
        client,
        file_path,
        parent_type=parent_type,
        parent_node=parent_node,
        doc_id=str(getattr(args, "doc_id", "") or ""),
    )
    return {"file_token": data.get("file_token"), "file_name": os.path.basename(file_path), "size": Path(file_path).stat().st_size}


def _cmd_docs_media_insert(args: argparse.Namespace) -> Mapping[str, Any]:
    file_path = str(getattr(args, "file", "") or "").strip()
    doc = _document_token(getattr(args, "doc", ""))
    media_type = str(getattr(args, "type", "") or "image").strip()
    client = _build_client(args)
    root_data = _data(client.request_json("GET", f"/docx/v1/documents/{quote(doc, safe='')}/blocks/{quote(doc, safe='')}"))
    block = root_data.get("block")
    block_map = block if isinstance(block, Mapping) else {}
    children = block_map.get("children")
    index = len(children) if isinstance(children, list) else 0
    create_payload = {
        "children": [
            {
                "block_type": 27 if media_type == "file" else 14,
                "index": index,
            }
        ],
        "index": index,
    }
    child_data = _data(
        client.request_json(
            "POST",
            f"/docx/v1/documents/{quote(doc, safe='')}/blocks/{quote(doc, safe='')}/children",
            payload=create_payload,
        )
    )
    children_out = child_data.get("children") if isinstance(child_data.get("children"), list) else []
    new_block = children_out[0] if children_out and isinstance(children_out[0], Mapping) else {}
    block_id = str(new_block.get("block_id") or "")
    parent_type = "docx_file" if media_type == "file" else "docx_image"
    upload = _media_upload(client, file_path, parent_type=parent_type, parent_node=block_id, doc_id=doc)
    file_token = str(upload.get("file_token") or "")
    update_body = {
        "requests": [
            {
                "block_id": block_id,
                media_type: {
                    "token": file_token,
                    "caption": str(getattr(args, "caption", "") or ""),
                },
            }
        ]
    }
    update_data = _data(
        client.request_json(
            "PATCH",
            f"/docx/v1/documents/{quote(doc, safe='')}/blocks/batch_update",
            payload=update_body,
        )
    )
    return {"block_id": block_id, "file_token": file_token, **update_data}


def _download_to_output(args: argparse.Namespace, path: str, *, params: dict[str, Any] | None = None) -> Mapping[str, Any]:
    output = str(getattr(args, "output", "") or "").strip()
    if not output:
        raise ValueError("specify --output")
    target = Path(output)
    if target.exists() and not bool(getattr(args, "overwrite", False)):
        raise ValueError(f"output file already exists: {target}")
    client = _build_client(args)
    content, headers = _download_openapi_bytes(client, path, params=params)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return {"saved_path": str(target), "size_bytes": len(content), "content_type": headers.get("content-type")}


def _cmd_docs_media_download(args: argparse.Namespace) -> Mapping[str, Any]:
    token = str(getattr(args, "token", "") or "").strip()
    media_type = str(getattr(args, "type", "") or "media").strip()
    if not token:
        raise ValueError("specify --token")
    if media_type == "whiteboard":
        return _download_to_output(args, f"/board/v1/whiteboards/{quote(token, safe='')}/download_as_image")
    return _download_to_output(args, f"/drive/v1/medias/{quote(token, safe='')}/download")


def _cmd_docs_media_preview(args: argparse.Namespace) -> Mapping[str, Any]:
    token = str(getattr(args, "token", "") or "").strip()
    if not token:
        raise ValueError("specify --token")
    return _download_to_output(
        args,
        f"/drive/v1/medias/{quote(token, safe='')}/preview_download",
        params={"preview_type": "16"},
    )


__all__ = [
    "_cmd_docs_create",
    "_cmd_docs_fetch",
    "_cmd_docs_media_download",
    "_cmd_docs_media_insert",
    "_cmd_docs_media_preview",
    "_cmd_docs_media_upload",
    "_cmd_docs_search",
    "_cmd_docs_update",
    "_cmd_whiteboard_update",
]
