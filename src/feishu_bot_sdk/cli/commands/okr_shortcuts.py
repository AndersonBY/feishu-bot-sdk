from __future__ import annotations

import argparse
import json
from typing import Any, Mapping

from ..runtime import _build_client, _resolve_text_input, build_multipart_file


TARGET_TYPES = {"objective": 1, "key_result": 2}


def _cmd_okr_shortcut(args: argparse.Namespace) -> Mapping[str, Any]:
    command = str(getattr(args, "okr_command", "") or "")
    if command == "cycle-list":
        return _cmd_cycle_list(args)
    if command == "cycle-detail":
        return _cmd_cycle_detail(args)
    if command == "progress-list":
        return _cmd_progress_list(args)
    if command == "progress-get":
        return _cmd_progress_get(args)
    if command == "progress-create":
        return _cmd_progress_create(args)
    if command == "progress-update":
        return _cmd_progress_update(args)
    if command == "progress-delete":
        return _cmd_progress_delete(args)
    if command == "upload-image":
        return _cmd_upload_image(args)
    raise ValueError(f"unsupported okr shortcut: {command}")


def _cmd_cycle_list(args: argparse.Namespace) -> Mapping[str, Any]:
    params = {
        "user_id": _required_string(getattr(args, "user_id", None), name="user-id"),
        "user_id_type": _user_id_type(args),
        "page_size": 100,
    }
    time_range = _optional_string(getattr(args, "time_range", None))
    if time_range:
        params["time_range"] = time_range
    data = _data_or_raw(_build_client(args).request_json("GET", "/okr/v2/cycles", params=params))
    return _list_output(data)


def _cmd_cycle_detail(args: argparse.Namespace) -> Mapping[str, Any]:
    cycle_id = _required_string(getattr(args, "cycle_id", None), name="cycle-id")
    data = _data_or_raw(
        _build_client(args).request_json(
            "GET",
            f"/okr/v2/cycles/{cycle_id}/objectives",
            params={"page_size": 100},
        )
    )
    return _list_output(data)


def _cmd_progress_list(args: argparse.Namespace) -> Mapping[str, Any]:
    target_id = _required_string(getattr(args, "target_id", None), name="target-id")
    target_type = _target_type_name(args)
    path = (
        f"/okr/v2/objectives/{target_id}/progresses"
        if target_type == "objective"
        else f"/okr/v2/key_results/{target_id}/progresses"
    )
    data = _data_or_raw(
        _build_client(args).request_json(
            "GET",
            path,
            params={
                "user_id_type": _user_id_type(args),
                "department_id_type": _optional_string(getattr(args, "department_id_type", None)) or "open_department_id",
                "page_size": 100,
            },
        )
    )
    return _list_output(data)


def _cmd_progress_get(args: argparse.Namespace) -> Mapping[str, Any]:
    progress_id = _required_string(getattr(args, "progress_id", None), name="progress-id")
    response = _build_client(args).request_json(
        "GET",
        f"/okr/v1/progress_records/{progress_id}",
        params={"user_id_type": _user_id_type(args)},
    )
    return _data_or_raw(response)


def _cmd_progress_create(args: argparse.Namespace) -> Mapping[str, Any]:
    target_type_name = _target_type_name(args)
    payload = {
        "content": _content_block(args),
        "target_id": _required_string(getattr(args, "target_id", None), name="target-id"),
        "target_type": TARGET_TYPES[target_type_name],
        "progress_rate": _progress_rate(args),
        "source_title": _optional_string(getattr(args, "source_title", None)) or "created by lark-cli",
        "source_url": _optional_string(getattr(args, "source_url", None)),
    }
    response = _build_client(args).request_json(
        "POST",
        "/okr/v1/progress_records/",
        params={"user_id_type": _user_id_type(args)},
        payload=_drop_empty(payload),
    )
    return _data_or_raw(response)


def _cmd_progress_update(args: argparse.Namespace) -> Mapping[str, Any]:
    progress_id = _required_string(getattr(args, "progress_id", None), name="progress-id")
    payload = {
        "content": _content_block(args),
        "progress_rate": _progress_rate(args),
    }
    response = _build_client(args).request_json(
        "PUT",
        f"/okr/v1/progress_records/{progress_id}",
        params={"user_id_type": _user_id_type(args)},
        payload=_drop_empty(payload),
    )
    return _data_or_raw(response)


def _cmd_progress_delete(args: argparse.Namespace) -> Mapping[str, Any]:
    progress_id = _required_string(getattr(args, "progress_id", None), name="progress-id")
    response = _build_client(args).request_json("DELETE", f"/okr/v1/progress_records/{progress_id}")
    return _data_or_raw(response)


def _cmd_upload_image(args: argparse.Namespace) -> Mapping[str, Any]:
    target_type = _target_type_name(args)
    file_path = _required_string(getattr(args, "file", None), name="file")
    field, file_payload, _meta = build_multipart_file(file_path, default_field="data")
    response = _build_client(args).request_multipart(
        "POST",
        "/okr/v1/images/upload",
        data={
            "target_id": _required_string(getattr(args, "target_id", None), name="target-id"),
            "target_type": str(TARGET_TYPES[target_type]),
        },
        files={field: file_payload},
    )
    return _data_or_raw(response)


def _content_block(args: argparse.Namespace) -> dict[str, Any]:
    content = _resolve_text_input(
        text=getattr(args, "content", None),
        file_path=getattr(args, "content_file", None),
        stdin_enabled=bool(getattr(args, "content_stdin", False)),
        name="content",
    )
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"content must be valid JSON: {exc}") from exc
    if not isinstance(parsed, Mapping):
        raise ValueError("content must be a JSON object")
    return {str(key): value for key, value in parsed.items()}


def _progress_rate(args: argparse.Namespace) -> dict[str, Any] | None:
    percent = _optional_string(getattr(args, "progress_percent", None))
    status = _optional_string(getattr(args, "progress_status", None))
    payload: dict[str, Any] = {}
    if percent is not None:
        payload["percent"] = percent
    if status is not None:
        payload["status"] = status
    return payload or None


def _target_type_name(args: argparse.Namespace) -> str:
    value = _required_string(getattr(args, "target_type", None), name="target-type")
    if value not in TARGET_TYPES:
        raise ValueError("--target-type must be one of: objective | key_result")
    return value


def _user_id_type(args: argparse.Namespace) -> str:
    return _optional_string(getattr(args, "user_id_type", None)) or "open_id"


def _required_string(value: Any, *, name: str) -> str:
    text = _optional_string(value)
    if not text:
        raise ValueError(f"--{name} is required")
    return text


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _drop_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): value for key, value in payload.items() if value is not None}


def _data_or_raw(response: Mapping[str, Any]) -> dict[str, Any]:
    data = response.get("data")
    if isinstance(data, Mapping):
        return {str(key): value for key, value in data.items()}
    return {str(key): value for key, value in response.items()}


def _list_output(data: Mapping[str, Any]) -> dict[str, Any]:
    items = data.get("items")
    if not isinstance(items, list):
        items = []
    return {
        "items": items,
        "count": len(items),
        "has_more": bool(data.get("has_more")),
        "page_token": data.get("page_token"),
    }


__all__ = ["_cmd_okr_shortcut"]
