from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import quote

import httpx

from ...exceptions import HTTPRequestError
from ...docx import DocContentService
from ...drive import DriveFileService
from ..runtime import _build_client, infer_mime_type


def _optional_string(value: Any) -> str | None:
    text = str(value or "").strip()
    if text:
        return text
    return None


def _extract_response_data(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    data = payload.get("data")
    if isinstance(data, Mapping):
        return data
    return payload


def _data(response: Mapping[str, Any]) -> dict[str, Any]:
    data = response.get("data")
    if isinstance(data, Mapping):
        return {str(key): value for key, value in data.items()}
    return {}


def _split_csv(value: Any) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _result_payload(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    data = _extract_response_data(payload)
    result = data.get("result")
    if isinstance(result, Mapping):
        return result
    return data


def _job_status_label(job_status: int, *, success_token: str | None = None) -> str:
    if job_status == 0:
        return "success" if success_token else "pending"
    if job_status == 1:
        return "new"
    if job_status == 2:
        return "processing"
    if job_status == 3:
        return "internal_error"
    if job_status == 107:
        return "export_size_limit"
    if job_status == 108:
        return "timeout"
    if job_status == 109:
        return "export_block_not_permitted"
    if job_status == 110:
        return "no_permission"
    if job_status == 111:
        return "docs_deleted"
    if job_status == 122:
        return "export_denied_on_copying"
    if job_status == 123:
        return "docs_not_exist"
    if job_status == 6000:
        return "export_images_exceed_limit"
    return f"status_{job_status}"


def _drive_import_default_name(file_path: str) -> str:
    base = os.path.basename(file_path)
    stem, _ext = os.path.splitext(base)
    return stem or base


def _build_import_media_extra(file_path: str, doc_type: str) -> str:
    return json.dumps(
        {
            "obj_type": doc_type,
            "file_extension": os.path.splitext(file_path)[1].lstrip(".").lower(),
        },
        ensure_ascii=False,
    )


def _build_import_task_payload(file_path: str, *, file_token: str, doc_type: str, folder_token: str, name: str | None) -> dict[str, Any]:
    return {
        "file_extension": os.path.splitext(file_path)[1].lstrip(".").lower(),
        "file_token": file_token,
        "type": doc_type,
        "file_name": _optional_string(name) or _drive_import_default_name(file_path),
        "point": {
            "mount_type": 1,
            "mount_key": folder_token,
        },
    }


def _normalize_import_status(ticket: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    result = _result_payload(payload)
    token = _optional_string(result.get("token"))
    job_status = int(result.get("job_status") or 0)
    return {
        "scenario": "import",
        "ticket": ticket,
        "type": _optional_string(result.get("type")),
        "token": token,
        "url": _optional_string(result.get("url")),
        "job_status": job_status,
        "job_status_label": _job_status_label(job_status, success_token=token),
        "job_error_msg": _optional_string(result.get("job_error_msg")),
        "extra": result.get("extra"),
    }


def _normalize_export_status(ticket: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    result = _result_payload(payload)
    file_token = _optional_string(result.get("file_token"))
    job_status = int(result.get("job_status") or 0)
    return {
        "scenario": "export",
        "ticket": ticket,
        "type": _optional_string(result.get("type")),
        "file_extension": _optional_string(result.get("file_extension")),
        "file_name": _optional_string(result.get("file_name")),
        "file_token": file_token,
        "file_size": result.get("file_size"),
        "job_status": job_status,
        "job_status_label": _job_status_label(job_status, success_token=file_token),
        "job_error_msg": _optional_string(result.get("job_error_msg")),
    }


def _normalize_task_check_status(task_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    result = _result_payload(payload)
    status = _optional_string(result.get("status")) or "unknown"
    return {
        "scenario": "task_check",
        "task_id": task_id,
        "status": status,
        "ready": status.lower() == "success",
        "failed": status.lower() == "failed",
    }


def _poll_import_result(drive: DriveFileService, ticket: str, *, attempts: int, interval_seconds: float) -> dict[str, Any]:
    last = _normalize_import_status(ticket, drive.get_import_task(ticket))
    if last.get("token"):
        last["ready"] = True
        last["failed"] = False
        return last
    for _ in range(max(attempts - 1, 0)):
        time.sleep(max(interval_seconds, 0.0))
        last = _normalize_import_status(ticket, drive.get_import_task(ticket))
        if last.get("token"):
            last["ready"] = True
            last["failed"] = False
            return last
        if last["job_status"] not in {0, 1, 2}:
            last["ready"] = False
            last["failed"] = True
            return last
    last["ready"] = False
    last["failed"] = last["job_status"] not in {0, 1, 2}
    return last


def _poll_export_result(
    drive: DriveFileService,
    ticket: str,
    *,
    source_token: str,
    attempts: int,
    interval_seconds: float,
) -> dict[str, Any]:
    last = _normalize_export_status(ticket, drive.get_export_task(ticket, token=source_token))
    if last.get("file_token"):
        last["ready"] = True
        last["failed"] = False
        return last
    for _ in range(max(attempts - 1, 0)):
        time.sleep(max(interval_seconds, 0.0))
        last = _normalize_export_status(ticket, drive.get_export_task(ticket, token=source_token))
        if last.get("file_token"):
            last["ready"] = True
            last["failed"] = False
            return last
        if last["job_status"] not in {0, 1, 2}:
            last["ready"] = False
            last["failed"] = True
            return last
    last["ready"] = False
    last["failed"] = last["job_status"] not in {0, 1, 2}
    return last


def _poll_task_check_result(
    drive: DriveFileService,
    task_id: str,
    *,
    attempts: int,
    interval_seconds: float,
) -> dict[str, Any]:
    last = _normalize_task_check_status(task_id, drive.get_task_status(task_id))
    if last["ready"] or last["failed"]:
        return last
    for _ in range(max(attempts - 1, 0)):
        time.sleep(max(interval_seconds, 0.0))
        last = _normalize_task_check_status(task_id, drive.get_task_status(task_id))
        if last["ready"] or last["failed"]:
            return last
    return last


def _ensure_output_file(
    *,
    output_dir: str | None,
    filename: str,
    overwrite: bool,
    content: bytes,
) -> str:
    directory = Path(output_dir or ".")
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / filename
    if target.exists() and not overwrite:
        raise ValueError(f"output file already exists: {target}")
    target.write_bytes(content)
    return str(target)


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


def _safe_filename_component(value: str) -> str:
    cleaned = "".join("_" if char in '/\\\0' else char for char in value).strip()
    return cleaned or "export"


def _extension_for_export(file_extension: str) -> str:
    if file_extension == "markdown":
        return ".md"
    return f".{file_extension}"


def _ensure_export_filename(name: str | None, token: str, file_extension: str) -> str:
    base = _safe_filename_component(name or token)
    suffix = _extension_for_export(file_extension)
    if base.lower().endswith(suffix.lower()):
        return base
    return f"{base}{suffix}"


def _fetch_drive_title(drive: DriveFileService, token: str, doc_type: str) -> str | None:
    try:
        payload = drive.batch_query_metas([{"doc_token": token, "doc_type": doc_type}])
    except Exception:
        return None
    data = _extract_response_data(payload)
    metas = data.get("metas")
    if not isinstance(metas, list) or not metas:
        return None
    first = metas[0]
    if not isinstance(first, Mapping):
        return None
    return _optional_string(first.get("title"))


def _cmd_drive_import_shortcut(args: argparse.Namespace) -> Mapping[str, Any]:
    file_path = str(args.file_path)
    doc_type = str(args.type).strip().lower()
    folder_token = _optional_string(getattr(args, "folder_token", None)) or ""
    name = _optional_string(getattr(args, "name", None))
    attempts = int(getattr(args, "poll_attempts", 6))
    interval_seconds = float(getattr(args, "poll_interval", 2.0))

    client = _build_client(args)
    drive = DriveFileService(client)

    upload_result = drive.upload_media(
        file_path,
        parent_type="ccm_import_open",
        parent_node="",
        file_name=os.path.basename(file_path),
        extra=_build_import_media_extra(file_path, doc_type),
    )
    upload_data = _extract_response_data(upload_result)
    file_token = _optional_string(upload_data.get("file_token"))
    if not file_token:
        raise ValueError("drive import upload did not return file_token")

    task_result = drive.create_import_task(
        _build_import_task_payload(
            file_path,
            file_token=file_token,
            doc_type=doc_type,
            folder_token=folder_token,
            name=name,
        )
    )
    task_data = _extract_response_data(task_result)
    ticket = _optional_string(task_data.get("ticket"))
    if not ticket:
        raise ValueError("drive import task creation did not return ticket")

    status = _poll_import_result(drive, ticket, attempts=attempts, interval_seconds=interval_seconds)
    status["uploaded_file_token"] = file_token
    if status["ready"] or status["failed"]:
        return status
    status["timed_out"] = True
    status["next_command"] = f"feishu drive +task_result --scenario import --ticket {ticket}"
    return status


def _cmd_drive_export_shortcut(args: argparse.Namespace) -> Mapping[str, Any]:
    token = str(args.token)
    doc_type = str(args.doc_type).strip().lower()
    file_extension = str(args.file_extension).strip().lower()
    output_dir = _optional_string(getattr(args, "output_dir", None)) or "."
    overwrite = bool(getattr(args, "overwrite", False))

    client = _build_client(args)
    drive = DriveFileService(client)

    if file_extension == "markdown":
        if doc_type != "docx":
            raise ValueError("--file-extension markdown only supports --doc-type docx")
        content_service = DocContentService(client)
        content_result = content_service.get_content(token, doc_type="docx", content_type="markdown")
        content_data = _extract_response_data(content_result)
        content = content_data.get("content")
        if not isinstance(content, str):
            raise ValueError("docx markdown export did not return content")
        file_name = _ensure_export_filename(_fetch_drive_title(drive, token, doc_type), token, file_extension)
        saved_path = _ensure_output_file(
            output_dir=output_dir,
            filename=file_name,
            overwrite=overwrite,
            content=content.encode("utf-8"),
        )
        return {
            "scenario": "export",
            "token": token,
            "type": doc_type,
            "file_extension": file_extension,
            "file_name": file_name,
            "saved_path": saved_path,
            "size_bytes": len(content.encode("utf-8")),
            "ready": True,
            "failed": False,
        }

    task_payload: dict[str, Any] = {
        "token": token,
        "type": doc_type,
        "file_extension": file_extension,
    }
    sub_id = _optional_string(getattr(args, "sub_id", None))
    if sub_id:
        task_payload["sub_id"] = sub_id
    task_result = drive.create_export_task(task_payload)
    task_data = _extract_response_data(task_result)
    ticket = _optional_string(task_data.get("ticket"))
    if not ticket:
        raise ValueError("drive export task creation did not return ticket")

    attempts = int(getattr(args, "poll_attempts", 6))
    interval_seconds = float(getattr(args, "poll_interval", 2.0))
    status = _poll_export_result(
        drive,
        ticket,
        source_token=token,
        attempts=attempts,
        interval_seconds=interval_seconds,
    )
    if status["ready"]:
        export_file_token = _optional_string(status.get("file_token"))
        if not export_file_token:
            raise ValueError("drive export task completed without file_token")
        content = drive.download_export_file(export_file_token)
        file_name = _ensure_export_filename(
            _optional_string(status.get("file_name")) or _fetch_drive_title(drive, token, doc_type),
            token,
            file_extension,
        )
        saved_path = _ensure_output_file(
            output_dir=output_dir,
            filename=file_name,
            overwrite=overwrite,
            content=content,
        )
        status["saved_path"] = saved_path
        status["size_bytes"] = len(content)
        return status
    if status["failed"]:
        return status
    status["timed_out"] = True
    status["next_command"] = f"feishu drive +task_result --scenario export --ticket {ticket} --file-token {token}"
    return status


def _cmd_drive_move_shortcut(args: argparse.Namespace) -> Mapping[str, Any]:
    file_token = str(args.file_token)
    file_type = str(args.type).strip().lower()

    client = _build_client(args)
    drive = DriveFileService(client)

    folder_token = _optional_string(getattr(args, "folder_token", None))
    if not folder_token:
        root_meta = drive.get_root_folder_meta()
        root_data = _extract_response_data(root_meta)
        folder_token = _optional_string(root_data.get("token"))
        if not folder_token:
            raise ValueError("drive root folder lookup did not return token")

    move_result = drive.move_file(file_token, type=file_type, folder_token=folder_token)
    move_data = _extract_response_data(move_result)
    task_id = _optional_string(move_data.get("task_id"))

    if file_type != "folder" or not task_id:
        return {
            "file_token": file_token,
            "folder_token": folder_token,
            "type": file_type,
            **{str(key): value for key, value in move_data.items()},
        }

    attempts = int(getattr(args, "poll_attempts", 6))
    interval_seconds = float(getattr(args, "poll_interval", 2.0))
    status = _poll_task_check_result(
        drive,
        task_id,
        attempts=attempts,
        interval_seconds=interval_seconds,
    )
    status["file_token"] = file_token
    status["folder_token"] = folder_token
    if status["ready"] or status["failed"]:
        return status
    status["timed_out"] = True
    status["next_command"] = f"feishu drive +task_result --scenario task_check --task-id {task_id}"
    return status


def _cmd_drive_upload(args: argparse.Namespace) -> Mapping[str, Any]:
    file_path = str(getattr(args, "file", "") or "").strip()
    if not file_path:
        raise ValueError("specify --file")
    file_bytes = Path(file_path).read_bytes()
    file_name = _optional_string(getattr(args, "name", None)) or os.path.basename(file_path)
    wiki_token = _optional_string(getattr(args, "wiki_token", None))
    folder_token = _optional_string(getattr(args, "folder_token", None))
    if wiki_token and folder_token:
        raise ValueError("--folder-token and --wiki-token are mutually exclusive")
    parent_type = "wiki" if wiki_token else "explorer"
    parent_node = wiki_token or folder_token or ""
    client = _build_client(args)
    data = _data(
        client.request_multipart(
            "POST",
            "/drive/v1/files/upload_all",
            data={
                "file_name": file_name,
                "parent_type": parent_type,
                "parent_node": parent_node,
                "size": len(file_bytes),
            },
            files={"file": (file_name, file_bytes, infer_mime_type(file_path))},
        )
    )
    return {
        "file_token": data.get("file_token"),
        "file_name": file_name,
        "size": len(file_bytes),
        "parent_type": parent_type,
        "parent_node": parent_node,
    }


def _cmd_drive_download(args: argparse.Namespace) -> Mapping[str, Any]:
    file_token = str(getattr(args, "file_token", "") or "").strip()
    if not file_token:
        raise ValueError("specify --file-token")
    output = str(getattr(args, "output", "") or file_token)
    overwrite = bool(getattr(args, "overwrite", False))
    target = Path(output)
    if target.exists() and not overwrite:
        raise ValueError(f"output file already exists: {target}")
    client = _build_client(args)
    content, headers = _download_openapi_bytes(client, f"/drive/v1/files/{quote(file_token, safe='')}/download")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return {
        "saved_path": str(target),
        "size_bytes": len(content),
        "content_type": headers.get("content-type"),
    }


def _cmd_drive_create_folder(args: argparse.Namespace) -> Mapping[str, Any]:
    name = str(getattr(args, "name", "") or "").strip()
    if not name:
        raise ValueError("specify --name")
    folder_token = str(getattr(args, "folder_token", "") or "").strip()
    client = _build_client(args)
    data = _data(
        client.request_json(
            "POST",
            "/drive/v1/files/create_folder",
            payload={"name": name, "folder_token": folder_token},
        )
    )
    return {
        "created": True,
        "name": name,
        "folder_token": data.get("token"),
        "parent_folder_token": folder_token,
        "url": data.get("url"),
    }


def _cmd_drive_create_shortcut(args: argparse.Namespace) -> Mapping[str, Any]:
    file_token = str(getattr(args, "file_token", "") or "").strip()
    file_type = str(getattr(args, "type", "") or "").strip().lower()
    folder_token = str(getattr(args, "folder_token", "") or "").strip()
    if not file_token or not file_type or not folder_token:
        raise ValueError("specify --file-token, --type, and --folder-token")
    body = {
        "parent_token": folder_token,
        "refer_entity": {"refer_token": file_token, "refer_type": file_type},
    }
    client = _build_client(args)
    data = _data(client.request_json("POST", "/drive/v1/files/create_shortcut", payload=body))
    node = data.get("succ_shortcut_node")
    node_map = node if isinstance(node, Mapping) else {}
    return {
        "created": True,
        "source_file_token": file_token,
        "source_type": file_type,
        "folder_token": folder_token,
        "shortcut_token": node_map.get("token"),
        "url": node_map.get("url"),
        "title": node_map.get("name"),
    }


def _cmd_drive_delete(args: argparse.Namespace) -> Mapping[str, Any]:
    file_token = str(getattr(args, "file_token", "") or "").strip()
    file_type = str(getattr(args, "type", "") or "").strip().lower()
    if not file_token or not file_type:
        raise ValueError("specify --file-token and --type")
    client = _build_client(args)
    data = _data(
        client.request_json(
            "DELETE",
            f"/drive/v1/files/{quote(file_token, safe='')}",
            params={"type": file_type},
        )
    )
    return {"deleted": True, "file_token": file_token, "type": file_type, **data}


def _cmd_drive_apply_permission(args: argparse.Namespace) -> Mapping[str, Any]:
    token = str(getattr(args, "token", "") or "").strip()
    doc_type = str(getattr(args, "type", "") or "").strip()
    perm = str(getattr(args, "perm", "") or "").strip()
    if not token or not doc_type or not perm:
        raise ValueError("specify --token, --type, and --perm")
    body: dict[str, Any] = {"perm": perm}
    remark = str(getattr(args, "remark", "") or "").strip()
    if remark:
        body["remark"] = remark
    client = _build_client(args)
    return _data(
        client.request_json(
            "POST",
            f"/drive/v1/permissions/{quote(token, safe='')}/members/apply",
            params={"type": doc_type},
            payload=body,
        )
    )


def _comment_reply_elements(value: str) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError("--content must be valid reply_elements JSON") from exc
    if not isinstance(parsed, list):
        raise ValueError("--content must be a JSON array")
    return [dict(item) for item in parsed if isinstance(item, Mapping)]


def _cmd_drive_add_comment(args: argparse.Namespace) -> Mapping[str, Any]:
    doc_token = str(getattr(args, "doc", "") or "").strip()
    doc_type = str(getattr(args, "type", "") or "").strip() or "docx"
    content = str(getattr(args, "content", "") or "").strip()
    if not doc_token or not content:
        raise ValueError("specify --doc and --content")
    body: dict[str, Any] = {
        "file_type": doc_type,
        "reply_elements": _comment_reply_elements(content),
    }
    block_id = str(getattr(args, "block_id", "") or "").strip()
    if block_id:
        body["block_id"] = block_id
    if bool(getattr(args, "full_comment", False)):
        body["is_whole"] = True
    client = _build_client(args)
    return _data(
        client.request_json(
            "POST",
            f"/drive/v1/files/{quote(doc_token, safe='')}/new_comments",
            payload=body,
        )
    )


def _cmd_drive_search(args: argparse.Namespace) -> Mapping[str, Any]:
    body: dict[str, Any] = {
        "query": str(getattr(args, "query", "") or ""),
        "page_size": int(getattr(args, "page_size", 15) or 15),
    }
    page_token = _optional_string(getattr(args, "page_token", None))
    if page_token:
        body["page_token"] = page_token
    doc_filter: dict[str, Any] = {}
    doc_types = _split_csv(getattr(args, "doc_types", None))
    if doc_types:
        doc_filter["doc_types"] = [item.upper() for item in doc_types]
    folder_tokens = _split_csv(getattr(args, "folder_tokens", None))
    if folder_tokens:
        doc_filter["folder_tokens"] = folder_tokens
    wiki_filter: dict[str, Any] = {}
    space_ids = _split_csv(getattr(args, "space_ids", None))
    if space_ids:
        wiki_filter["space_ids"] = space_ids
    body["doc_filter"] = doc_filter
    body["wiki_filter"] = wiki_filter
    client = _build_client(args)
    data = _data(client.request_json("POST", "/search/v2/doc_wiki/search", payload=body))
    items = data.get("res_units") if isinstance(data.get("res_units"), list) else []
    return {
        "total": data.get("total"),
        "has_more": data.get("has_more"),
        "page_token": data.get("page_token"),
        "results": items,
    }


def _cmd_drive_export_download(args: argparse.Namespace) -> Mapping[str, Any]:
    file_token = str(getattr(args, "file_token", "") or "").strip()
    if not file_token:
        raise ValueError("specify --file-token")
    output_dir = _optional_string(getattr(args, "output_dir", None)) or "."
    file_name = _optional_string(getattr(args, "file_name", None)) or file_token
    overwrite = bool(getattr(args, "overwrite", False))
    client = _build_client(args)
    content, headers = _download_openapi_bytes(
        client,
        f"/drive/v1/export_tasks/file/{quote(file_token, safe='')}/download",
    )
    saved_path = _ensure_output_file(
        output_dir=output_dir,
        filename=file_name,
        overwrite=overwrite,
        content=content,
    )
    return {
        "saved_path": saved_path,
        "size_bytes": len(content),
        "content_type": headers.get("content-type"),
    }


def _cmd_drive_task_result_shortcut(args: argparse.Namespace) -> Mapping[str, Any]:
    scenario = str(args.scenario).strip().lower()
    client = _build_client(args)
    drive = DriveFileService(client)

    if scenario == "import":
        ticket = _optional_string(getattr(args, "ticket", None))
        if not ticket:
            raise ValueError("--ticket is required for import scenario")
        status = _normalize_import_status(ticket, drive.get_import_task(ticket))
        status["ready"] = bool(status.get("token"))
        status["failed"] = not status["ready"] and status["job_status"] not in {0, 1, 2}
        return status

    if scenario == "export":
        ticket = _optional_string(getattr(args, "ticket", None))
        file_token = _optional_string(getattr(args, "file_token", None))
        if not ticket:
            raise ValueError("--ticket is required for export scenario")
        if not file_token:
            raise ValueError("--file-token is required for export scenario")
        status = _normalize_export_status(ticket, drive.get_export_task(ticket, token=file_token))
        status["ready"] = bool(status.get("file_token"))
        status["failed"] = not status["ready"] and status["job_status"] not in {0, 1, 2}
        return status

    if scenario == "task_check":
        task_id = _optional_string(getattr(args, "task_id", None))
        if not task_id:
            raise ValueError("--task-id is required for task_check scenario")
        return _normalize_task_check_status(task_id, drive.get_task_status(task_id))

    raise ValueError("unsupported scenario: use import, export, or task_check")


__all__ = [
    "_cmd_drive_add_comment",
    "_cmd_drive_apply_permission",
    "_cmd_drive_create_folder",
    "_cmd_drive_create_shortcut",
    "_cmd_drive_delete",
    "_cmd_drive_download",
    "_cmd_drive_export_shortcut",
    "_cmd_drive_export_download",
    "_cmd_drive_import_shortcut",
    "_cmd_drive_move_shortcut",
    "_cmd_drive_search",
    "_cmd_drive_task_result_shortcut",
    "_cmd_drive_upload",
]
