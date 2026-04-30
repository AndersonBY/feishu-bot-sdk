from __future__ import annotations

import argparse
import json
from typing import Any, Mapping

from ..runtime import _build_client, build_multipart_file


BASE_SHORTCUT_NAMES = (
    "table-list",
    "table-get",
    "table-create",
    "table-update",
    "table-delete",
    "field-list",
    "field-get",
    "field-create",
    "field-update",
    "field-delete",
    "field-search-options",
    "view-list",
    "view-get",
    "view-create",
    "view-delete",
    "view-get-filter",
    "view-set-filter",
    "view-get-visible-fields",
    "view-set-visible-fields",
    "view-get-group",
    "view-set-group",
    "view-get-sort",
    "view-set-sort",
    "view-get-timebar",
    "view-set-timebar",
    "view-get-card",
    "view-set-card",
    "view-rename",
    "record-list",
    "record-search",
    "record-get",
    "record-upsert",
    "record-batch-create",
    "record-batch-update",
    "record-share-link-create",
    "record-upload-attachment",
    "record-delete",
    "record-history-list",
    "base-get",
    "base-copy",
    "base-create",
    "role-create",
    "role-delete",
    "role-update",
    "role-list",
    "role-get",
    "advperm-enable",
    "advperm-disable",
    "workflow-list",
    "workflow-get",
    "workflow-create",
    "workflow-update",
    "workflow-enable",
    "workflow-disable",
    "data-query",
    "form-create",
    "form-delete",
    "form-list",
    "form-update",
    "form-get",
    "form-questions-create",
    "form-questions-delete",
    "form-questions-update",
    "form-questions-list",
    "dashboard-list",
    "dashboard-get",
    "dashboard-create",
    "dashboard-update",
    "dashboard-delete",
    "dashboard-arrange",
    "dashboard-block-list",
    "dashboard-block-get",
    "dashboard-block-create",
    "dashboard-block-update",
    "dashboard-block-delete",
)


VIEW_PROPERTY_SEGMENTS = {
    "view-get-filter": "filter",
    "view-set-filter": "filter",
    "view-get-visible-fields": "visible_fields",
    "view-set-visible-fields": "visible_fields",
    "view-get-group": "group",
    "view-set-group": "group",
    "view-get-sort": "sort",
    "view-set-sort": "sort",
    "view-get-timebar": "timebar",
    "view-set-timebar": "timebar",
    "view-get-card": "card",
    "view-set-card": "card",
}


def _cmd_base_shortcut(args: argparse.Namespace) -> Mapping[str, Any]:
    command = str(getattr(args, "base_command", "") or "")
    if command == "record-upsert":
        return _record_upsert(args)
    if command == "record-upload-attachment":
        return _record_upload_attachment(args)
    spec = _build_request(args, command)
    response = _build_client(args).request_json(
        spec["method"],
        spec["path"],
        params=spec.get("params"),
        payload=spec.get("payload"),
    )
    return _data_or_raw(response)


def _build_request(args: argparse.Namespace, command: str) -> dict[str, Any]:
    if command == "base-create":
        return _base_request(args, command, "")
    base_token = _base_token(args)
    table_id = _optional_string(getattr(args, "table_id", None))
    if command.startswith("table-"):
        return _table_request(args, command, base_token)
    if command.startswith("field-"):
        return _field_request(args, command, base_token, _required(table_id, "table-id"))
    if command.startswith("view-"):
        return _view_request(args, command, base_token, _required(table_id, "table-id"))
    if command.startswith("record-"):
        return _record_request(args, command, base_token, _required(table_id, "table-id"))
    if command.startswith("base-"):
        return _base_request(args, command, base_token)
    if command.startswith("role-"):
        return _role_request(args, command, base_token)
    if command.startswith("advperm-"):
        enabled = command == "advperm-enable"
        return {"method": "PUT", "path": f"/base/v3/bases/{base_token}/advperm/enable", "params": {"enable": enabled}}
    if command.startswith("workflow-"):
        return _workflow_request(args, command, base_token)
    if command == "data-query":
        return {"method": "POST", "path": f"/base/v3/bases/{base_token}/data/query", "payload": _json_object(args, "dsl")}
    if command.startswith("form-"):
        return _form_request(args, command, base_token, _required(table_id, "table-id"))
    if command.startswith("dashboard-"):
        return _dashboard_request(args, command, base_token)
    raise ValueError(f"unsupported base shortcut: {command}")


def _table_request(args: argparse.Namespace, command: str, base_token: str) -> dict[str, Any]:
    root = f"/base/v3/bases/{base_token}/tables"
    if command == "table-list":
        return {"method": "GET", "path": root, "params": {"offset": int(getattr(args, "offset", 0) or 0), "limit": int(getattr(args, "limit", 50) or 50)}}
    if command == "table-create":
        return {"method": "POST", "path": root, "payload": _drop_empty({"name": _required_attr(args, "name")})}
    table_id = _required_attr(args, "table_id")
    if command == "table-get":
        return {"method": "GET", "path": f"{root}/{table_id}"}
    if command == "table-update":
        return {"method": "PATCH", "path": f"{root}/{table_id}", "payload": _drop_empty({"name": _optional_string(getattr(args, "name", None))})}
    if command == "table-delete":
        return {"method": "DELETE", "path": f"{root}/{table_id}"}
    raise ValueError(f"unsupported table shortcut: {command}")


def _field_request(args: argparse.Namespace, command: str, base_token: str, table_id: str) -> dict[str, Any]:
    root = f"/base/v3/bases/{base_token}/tables/{table_id}/fields"
    if command == "field-list":
        return {"method": "GET", "path": root, "params": {"offset": int(getattr(args, "offset", 0) or 0), "limit": int(getattr(args, "limit", 100) or 100)}}
    if command == "field-create":
        return {"method": "POST", "path": root, "payload": _json_object(args, "json")}
    field_id = _required_attr(args, "field_id")
    if command == "field-get":
        return {"method": "GET", "path": f"{root}/{field_id}"}
    if command == "field-update":
        return {"method": "PUT", "path": f"{root}/{field_id}", "payload": _json_object(args, "json")}
    if command == "field-delete":
        return {"method": "DELETE", "path": f"{root}/{field_id}"}
    if command == "field-search-options":
        params = {"offset": int(getattr(args, "offset", 0) or 0), "limit": int(getattr(args, "limit", 30) or 30)}
        keyword = _optional_string(getattr(args, "keyword", None))
        if keyword:
            params["query"] = keyword
        return {"method": "GET", "path": f"{root}/{field_id}/options", "params": params}
    raise ValueError(f"unsupported field shortcut: {command}")


def _view_request(args: argparse.Namespace, command: str, base_token: str, table_id: str) -> dict[str, Any]:
    root = f"/base/v3/bases/{base_token}/tables/{table_id}/views"
    if command == "view-list":
        return {"method": "GET", "path": root, "params": {"offset": int(getattr(args, "offset", 0) or 0), "limit": int(getattr(args, "limit", 100) or 100)}}
    if command == "view-create":
        return {"method": "POST", "path": root, "payload": _json_value(args, "json")}
    view_id = _required_attr(args, "view_id")
    if command == "view-get":
        return {"method": "GET", "path": f"{root}/{view_id}"}
    if command == "view-delete":
        return {"method": "DELETE", "path": f"{root}/{view_id}"}
    if command == "view-rename":
        return {"method": "PATCH", "path": f"{root}/{view_id}", "payload": {"name": _required_attr(args, "name")}}
    segment = VIEW_PROPERTY_SEGMENTS.get(command)
    if not segment:
        raise ValueError(f"unsupported view shortcut: {command}")
    method = "GET" if command.startswith("view-get-") else "PUT"
    payload = None if method == "GET" else _json_value(args, "json")
    return {"method": method, "path": f"{root}/{view_id}/{segment}", "payload": payload}


def _record_request(args: argparse.Namespace, command: str, base_token: str, table_id: str) -> dict[str, Any]:
    root = f"/base/v3/bases/{base_token}/tables/{table_id}/records"
    if command == "record-list":
        params: dict[str, Any] = {"offset": int(getattr(args, "offset", 0) or 0), "limit": int(getattr(args, "limit", 100) or 100)}
        if view_id := _optional_string(getattr(args, "view_id", None)):
            params["view_id"] = view_id
        field_ids = _split_values(getattr(args, "field_id", None))
        if field_ids:
            params["field_id"] = field_ids
        return {"method": "GET", "path": root, "params": params}
    if command == "record-search":
        return {"method": "POST", "path": f"{root}/search", "payload": _json_object(args, "json")}
    if command == "record-batch-create":
        return {"method": "POST", "path": f"{root}/batch_create", "payload": _json_object(args, "json")}
    if command == "record-batch-update":
        return {"method": "POST", "path": f"{root}/batch_update", "payload": _json_object(args, "json")}
    if command == "record-share-link-create":
        return {"method": "POST", "path": f"{root}/share_links/batch", "payload": {"record_ids": _split_values(_required_attr(args, "record_ids"))}}
    if command == "record-history-list":
        params: dict[str, Any] = {
            "table_id": table_id,
            "record_id": _required_attr(args, "record_id"),
            "page_size": int(getattr(args, "page_size", 100) or 100),
        }
        if max_version := getattr(args, "max_version", None):
            params["max_version"] = int(max_version)
        return {"method": "GET", "path": f"/base/v3/bases/{base_token}/record_history", "params": params}
    record_id = _required_attr(args, "record_id")
    if command == "record-get":
        return {"method": "GET", "path": f"{root}/{record_id}"}
    if command == "record-delete":
        return {"method": "DELETE", "path": f"{root}/{record_id}"}
    raise ValueError(f"unsupported record shortcut: {command}")


def _record_upsert(args: argparse.Namespace) -> Mapping[str, Any]:
    base_token = _base_token(args)
    table_id = _required_attr(args, "table_id")
    fields = _json_object(args, "json")
    record_id = _optional_string(getattr(args, "record_id", None))
    if record_id:
        response = _build_client(args).request_json(
            "PATCH",
            f"/base/v3/bases/{base_token}/tables/{table_id}/records/{record_id}",
            payload={"fields": fields},
        )
    else:
        response = _build_client(args).request_json(
            "POST",
            f"/base/v3/bases/{base_token}/tables/{table_id}/records",
            payload={"fields": fields},
        )
    return _data_or_raw(response)


def _record_upload_attachment(args: argparse.Namespace) -> Mapping[str, Any]:
    base_token = _base_token(args)
    table_id = _required_attr(args, "table_id")
    record_id = _required_attr(args, "record_id")
    field_id = _required_attr(args, "field_id")
    file_path = _required_attr(args, "file")
    field, file_payload, _meta = build_multipart_file(file_path, default_field="file")
    file_name = _optional_string(getattr(args, "name", None)) or file_payload[0]
    client = _build_client(args)
    upload_data = _data_or_raw(
        client.request_multipart(
            "POST",
            "/drive/v1/medias/upload_all",
            data={"file_name": file_name, "parent_type": "bitable_file", "parent_node": base_token, "size": len(file_payload[1])},
            files={field: (file_name, file_payload[1], file_payload[2])},
        )
    )
    file_token = _optional_string(upload_data.get("file_token") or upload_data.get("file_key") or upload_data.get("token"))
    if not file_token:
        raise ValueError("upload response did not include file_token")
    response = client.request_json(
        "PATCH",
        f"/base/v3/bases/{base_token}/tables/{table_id}/records/{record_id}",
        payload={"fields": {field_id: [{"file_token": file_token, "name": file_name}]}},
    )
    return {"upload": upload_data, "record": _data_or_raw(response)}


def _base_request(args: argparse.Namespace, command: str, base_token: str) -> dict[str, Any]:
    if command == "base-create":
        return {
            "method": "POST",
            "path": "/base/v3/bases",
            "payload": _drop_empty(
                {
                    "name": _required_attr(args, "name"),
                    "folder_token": _optional_string(getattr(args, "folder_token", None)),
                    "time_zone": _optional_string(getattr(args, "time_zone", None)),
                }
            ),
        }
    if command == "base-get":
        return {"method": "GET", "path": f"/base/v3/bases/{base_token}"}
    if command == "base-copy":
        return {
            "method": "POST",
            "path": f"/base/v3/bases/{base_token}/copy",
            "payload": _drop_empty(
                {
                    "name": _optional_string(getattr(args, "name", None)),
                    "folder_token": _optional_string(getattr(args, "folder_token", None)),
                    "without_content": bool(getattr(args, "without_content", False)) or None,
                    "time_zone": _optional_string(getattr(args, "time_zone", None)),
                }
            ),
        }
    raise ValueError(f"unsupported base shortcut: {command}")


def _role_request(args: argparse.Namespace, command: str, base_token: str) -> dict[str, Any]:
    root = f"/base/v3/bases/{base_token}/roles"
    if command == "role-list":
        return {"method": "GET", "path": root}
    if command == "role-create":
        return {"method": "POST", "path": root, "payload": _json_object(args, "json")}
    role_id = _required_attr(args, "role_id")
    if command == "role-get":
        return {"method": "GET", "path": f"{root}/{role_id}"}
    if command == "role-update":
        return {"method": "PUT", "path": f"{root}/{role_id}", "payload": _json_object(args, "json")}
    if command == "role-delete":
        return {"method": "DELETE", "path": f"{root}/{role_id}"}
    raise ValueError(f"unsupported role shortcut: {command}")


def _workflow_request(args: argparse.Namespace, command: str, base_token: str) -> dict[str, Any]:
    root = f"/base/v3/bases/{base_token}/workflows"
    if command == "workflow-list":
        payload = _drop_empty({"status": _optional_string(getattr(args, "status", None)), "page_size": int(getattr(args, "page_size", 100) or 100)})
        return {"method": "POST", "path": f"{root}/list", "payload": payload}
    if command == "workflow-create":
        return {"method": "POST", "path": root, "payload": _json_object(args, "json")}
    workflow_id = _required_attr(args, "workflow_id")
    if command == "workflow-get":
        params = _drop_empty({"user_id_type": _optional_string(getattr(args, "user_id_type", None))})
        return {"method": "GET", "path": f"{root}/{workflow_id}", "params": params or None}
    if command == "workflow-update":
        return {"method": "PUT", "path": f"{root}/{workflow_id}", "payload": _json_object(args, "json")}
    if command in {"workflow-enable", "workflow-disable"}:
        return {"method": "PATCH", "path": f"{root}/{workflow_id}/{command.removeprefix('workflow-')}"}
    raise ValueError(f"unsupported workflow shortcut: {command}")


def _form_request(args: argparse.Namespace, command: str, base_token: str, table_id: str) -> dict[str, Any]:
    root = f"/base/v3/bases/{base_token}/tables/{table_id}/forms"
    if command == "form-list":
        return {"method": "GET", "path": root, "params": {"page_size": int(getattr(args, "page_size", 100) or 100)}}
    if command == "form-create":
        return {"method": "POST", "path": root, "payload": _drop_empty({"name": _required_attr(args, "name"), "description": _optional_string(getattr(args, "description", None))})}
    form_id = _required_attr(args, "form_id")
    if command == "form-get":
        return {"method": "GET", "path": f"{root}/{form_id}"}
    if command == "form-update":
        return {"method": "PATCH", "path": f"{root}/{form_id}", "payload": _drop_empty({"name": _optional_string(getattr(args, "name", None)), "description": _optional_string(getattr(args, "description", None))})}
    if command == "form-delete":
        return {"method": "DELETE", "path": f"{root}/{form_id}"}
    if command == "form-questions-list":
        return {"method": "GET", "path": f"{root}/{form_id}/questions"}
    if command == "form-questions-create":
        return {"method": "POST", "path": f"{root}/{form_id}/questions", "payload": {"questions": _json_array(args, "questions")}}
    question_id = _required_attr(args, "question_id")
    if command == "form-questions-update":
        return {"method": "PATCH", "path": f"{root}/{form_id}/questions/{question_id}", "payload": _json_object(args, "json")}
    if command == "form-questions-delete":
        return {"method": "DELETE", "path": f"{root}/{form_id}/questions/{question_id}"}
    raise ValueError(f"unsupported form shortcut: {command}")


def _dashboard_request(args: argparse.Namespace, command: str, base_token: str) -> dict[str, Any]:
    root = f"/base/v3/bases/{base_token}/dashboards"
    if command == "dashboard-list":
        return {"method": "GET", "path": root, "params": _paging_params(args)}
    if command == "dashboard-create":
        return {"method": "POST", "path": root, "payload": _dashboard_body(args, require_name=True)}
    dashboard_id = _required_attr(args, "dashboard_id")
    if command == "dashboard-get":
        return {"method": "GET", "path": f"{root}/{dashboard_id}"}
    if command == "dashboard-update":
        return {"method": "PATCH", "path": f"{root}/{dashboard_id}", "payload": _dashboard_body(args, require_name=False)}
    if command == "dashboard-delete":
        return {"method": "DELETE", "path": f"{root}/{dashboard_id}"}
    if command == "dashboard-arrange":
        return {"method": "POST", "path": f"{root}/{dashboard_id}/arrange", "payload": _json_object(args, "json")}
    block_root = f"{root}/{dashboard_id}/blocks"
    if command == "dashboard-block-list":
        return {"method": "GET", "path": block_root, "params": _paging_params(args)}
    if command == "dashboard-block-create":
        return {"method": "POST", "path": block_root, "payload": _dashboard_block_body(args)}
    block_id = _required_attr(args, "block_id")
    if command == "dashboard-block-get":
        params = _drop_empty({"user_id_type": _optional_string(getattr(args, "user_id_type", None))})
        return {"method": "GET", "path": f"{block_root}/{block_id}", "params": params or None}
    if command == "dashboard-block-update":
        return {"method": "PATCH", "path": f"{block_root}/{block_id}", "payload": _dashboard_block_body(args)}
    if command == "dashboard-block-delete":
        return {"method": "DELETE", "path": f"{block_root}/{block_id}"}
    raise ValueError(f"unsupported dashboard shortcut: {command}")


def _dashboard_body(args: argparse.Namespace, *, require_name: bool) -> dict[str, Any]:
    name = _required_attr(args, "name") if require_name else _optional_string(getattr(args, "name", None))
    body: dict[str, Any] = {}
    if name:
        body["name"] = name
    if theme_style := _optional_string(getattr(args, "theme_style", None)):
        body["theme"] = {"theme_style": theme_style}
    return body


def _dashboard_block_body(args: argparse.Namespace) -> dict[str, Any]:
    body = _drop_empty({"name": _optional_string(getattr(args, "name", None)), "type": _optional_string(getattr(args, "block_type", None))})
    if data_config := _optional_string(getattr(args, "data_config", None)):
        body["data_config"] = _loads_json(data_config, name="data-config")
    return body


def _paging_params(args: argparse.Namespace) -> dict[str, Any] | None:
    params = _drop_empty(
        {
            "page_size": getattr(args, "page_size", None),
            "page_token": _optional_string(getattr(args, "page_token", None)),
        }
    )
    return params or None


def _json_object(args: argparse.Namespace, attr: str) -> dict[str, Any]:
    parsed = _loads_json(_required_attr(args, attr), name=attr.replace("_", "-"))
    if not isinstance(parsed, Mapping):
        raise ValueError(f"--{attr.replace('_', '-')} must be a JSON object")
    return {str(key): value for key, value in parsed.items()}


def _json_array(args: argparse.Namespace, attr: str) -> list[Any]:
    parsed = _loads_json(_required_attr(args, attr), name=attr.replace("_", "-"))
    if not isinstance(parsed, list):
        raise ValueError(f"--{attr.replace('_', '-')} must be a JSON array")
    return parsed


def _json_value(args: argparse.Namespace, attr: str) -> Any:
    return _loads_json(_required_attr(args, attr), name=attr.replace("_", "-"))


def _loads_json(value: str, *, name: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{name} is not valid JSON: {exc}") from exc


def _base_token(args: argparse.Namespace) -> str:
    return _required_attr(args, "base_token")


def _required_attr(args: argparse.Namespace, attr: str) -> str:
    value = getattr(args, attr, None)
    if attr == "field_id" and isinstance(value, (list, tuple)):
        value = value[0] if value else None
    return _required(_optional_string(value), attr.replace("_", "-"))


def _required(value: str | None, name: str) -> str:
    if not value:
        raise ValueError(f"--{name} is required")
    return value


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _split_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        result: list[str] = []
        for item in value:
            result.extend(_split_values(item))
        return result
    return [item.strip() for item in str(value).split(",") if item.strip()]


def _drop_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): value for key, value in payload.items() if value is not None and value != {}}


def _data_or_raw(response: Mapping[str, Any]) -> dict[str, Any]:
    data = response.get("data")
    if isinstance(data, Mapping):
        return {str(key): value for key, value in data.items()}
    return {str(key): value for key, value in response.items()}


__all__ = ["BASE_SHORTCUT_NAMES", "_cmd_base_shortcut"]
