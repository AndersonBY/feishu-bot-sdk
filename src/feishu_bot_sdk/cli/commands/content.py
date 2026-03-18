from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from ...bitable import BitableService
from ...docx import DocContentService, DocxBlockService, DocxDocumentService, DocxService
from ...drive import DriveFileService, DrivePermissionService
from ...wiki import WikiService

from ..runtime import _build_client, _parse_json_array, _parse_json_object, _resolve_text_input


def _normalize_page_size(value: Any, *, default: int) -> int:
    if isinstance(value, int) and value > 0:
        return value
    return default


def _next_page_token(data: Mapping[str, Any]) -> str | None:
    token = data.get("page_token")
    if isinstance(token, str) and token:
        return token
    return None


def _has_more(data: Mapping[str, Any]) -> bool:
    return bool(data.get("has_more"))


def _optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
    return None


def _string_list(values: list[Any], *, name: str) -> list[str]:
    result: list[str] = []
    for item in values:
        if not isinstance(item, str) or not item:
            raise ValueError(f"{name} must be a JSON array of non-empty strings")
        result.append(item)
    return result


def _write_text_output(path_value: str, content: str) -> Path:
    output_path = Path(path_value)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return output_path


def _write_bytes_output(path_value: str, content: bytes) -> Path:
    output_path = Path(path_value)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(content)
    return output_path


def _write_json_output(path_value: str, payload: Mapping[str, Any]) -> Path:
    output_path = Path(path_value)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def _list_count(value: Any) -> int:
    if not isinstance(value, list):
        return 0
    return len(value)


def _count_inserted_relations(inserted_batches: Any) -> int:
    if not isinstance(inserted_batches, list):
        return 0
    total = 0
    for batch in inserted_batches:
        if not isinstance(batch, Mapping):
            continue
        total += _list_count(batch.get("block_id_relations"))
    return total


def _require_non_empty_string_arg(value: Any, *, name: str, example: str | None = None) -> str:
    normalized = str(value or "").strip()
    if normalized:
        return normalized
    message = f"{name} must not be empty"
    if example:
        message = f"{message}; example: {example}"
    raise ValueError(message)


def _optional_string(value: Any) -> str | None:
    normalized = str(value or "").strip()
    if normalized:
        return normalized
    return None


def _describe_bitable_table(item: Mapping[str, Any]) -> str:
    table_id = _optional_string(item.get("table_id")) or "<unknown>"
    table_name = _optional_string(item.get("name")) or _optional_string(item.get("table_name"))
    if table_name:
        return f"{table_id} ({table_name})"
    return table_id


def _list_bitable_tables(service: BitableService, app_token: str) -> list[Mapping[str, Any]]:
    return [item for item in service.iter_tables(app_token, page_size=100) if isinstance(item, Mapping)]


def _resolve_bitable_table_id(
    service: BitableService,
    app_token: str,
    *,
    table_id: Any,
    command_name: str,
) -> str:
    explicit_table_id = _optional_string(table_id)
    if explicit_table_id:
        return explicit_table_id

    app_info = service.get_app(app_token)
    app_payload = app_info.get("app") if isinstance(app_info, Mapping) else None
    if isinstance(app_payload, Mapping):
        default_table_id = _optional_string(app_payload.get("default_table_id"))
        if default_table_id:
            return default_table_id

    tables = _list_bitable_tables(service, app_token)
    if len(tables) == 1:
        only_table_id = _optional_string(tables[0].get("table_id"))
        if only_table_id:
            return only_table_id

    if not tables:
        raise ValueError(
            f"table-id is required for `{command_name}`; app `{app_token}` has no tables"
        )

    candidates = ", ".join(_describe_bitable_table(item) for item in tables[:5])
    if len(tables) > 5:
        candidates = f"{candidates}, ... ({len(tables)} tables total)"
    raise ValueError(
        f"table-id is required for `{command_name}`; app `{app_token}` has {len(tables)} tables and no default table id. "
        f"Run `feishu bitable list-tables --app-token {app_token} --format json` and choose one. "
        f"Candidates: {candidates}"
    )


def _result_to_plain_mapping(result: Mapping[str, Any]) -> dict[str, Any]:
    to_dict = getattr(result, "to_dict", None)
    if callable(to_dict):
        try:
            payload = to_dict(include_meta=True)
        except TypeError:
            payload = to_dict()
        if isinstance(payload, Mapping):
            return {str(key): value for key, value in payload.items()}
    return {str(key): value for key, value in result.items()}


def _augment_bitable_app_result(
    service: BitableService,
    result: Mapping[str, Any],
) -> Mapping[str, Any]:
    payload = _result_to_plain_mapping(result)
    data_payload: dict[str, Any]
    raw_data_payload = payload.get("data")
    if isinstance(raw_data_payload, Mapping):
        data_payload = dict(raw_data_payload)
        payload["data"] = data_payload
    else:
        data_payload = payload

    raw_app_payload = data_payload.get("app")
    if not isinstance(raw_app_payload, Mapping):
        return payload
    app_payload = dict(raw_app_payload)
    data_payload["app"] = app_payload

    app_token = _optional_string(app_payload.get("app_token"))
    if not app_token:
        return payload

    default_table_id = _optional_string(app_payload.get("default_table_id"))
    if default_table_id:
        data_payload.setdefault("table_id", default_table_id)
        return payload

    try:
        tables = _list_bitable_tables(service, app_token)
    except Exception:
        return payload

    if len(tables) == 1:
        only_table_id = _optional_string(tables[0].get("table_id"))
        only_table_name = _optional_string(tables[0].get("name")) or _optional_string(
            tables[0].get("table_name")
        )
        if only_table_id:
            app_payload["default_table_id"] = only_table_id
            data_payload["table_id"] = only_table_id
            if only_table_name:
                data_payload["table_name"] = only_table_name
        return payload

    if tables:
        data_payload["table_count"] = len(tables)
        data_payload["table_resolution_hint"] = (
            f"default table id is empty; run `feishu bitable list-tables --app-token {app_token} --format json` "
            "to choose a table. Table-specific commands can auto-resolve the table only when the app has exactly one table."
        )
    return payload


def _resolve_member_identity(
    args: argparse.Namespace,
    *,
    member_id: Any,
    member_id_type: Any,
) -> str:
    normalized_member_id = str(member_id or "").strip()
    if normalized_member_id and normalized_member_id.lower() not in {"me", "self", "current_user"}:
        return normalized_member_id

    normalized_id_type = str(member_id_type or "open_id").strip().lower() or "open_id"
    if normalized_id_type not in {"open_id", "user_id", "union_id"}:
        raise ValueError(f"unsupported member_id_type for current user resolution: {normalized_id_type}")

    user_info = _build_client(args, force_user_auth=True).get_user_info()
    resolved = getattr(user_info, normalized_id_type, None)
    if isinstance(resolved, str) and resolved.strip():
        return resolved.strip()
    raise ValueError(f"current authenticated user does not expose {normalized_id_type}; use another --member-id-type or pass explicit --member-id")


def _summarize_docx_insert_result(data: Mapping[str, Any], *, content: str) -> Mapping[str, Any]:
    converted = data.get("converted")
    inserted_batches = data.get("inserted_batches")
    image_replacements = data.get("image_replacements")

    converted_block_count = 0
    first_level_block_count = 0
    if isinstance(converted, Mapping):
        converted_block_count = _list_count(converted.get("blocks"))
        first_level_block_count = _list_count(converted.get("first_level_block_ids"))

    summary: dict[str, Any] = {
        "ok": bool(data.get("ok", True)),
        "document_id": data.get("document_id"),
        "block_id": data.get("block_id"),
        "content_type": data.get("content_type"),
        "input_char_count": len(content),
        "batch_count": int(data.get("batch_count", _list_count(inserted_batches))),
        "first_level_block_count": first_level_block_count,
        "converted_block_count": converted_block_count,
        "inserted_block_count": _count_inserted_relations(inserted_batches),
        "image_replacement_count": _list_count(image_replacements),
    }
    return {key: value for key, value in summary.items() if value is not None}


def _collect_all_pages(
    fetch_page: Callable[..., Mapping[str, Any]],
    *,
    page_size: int | None,
    page_token: str | None,
    default_page_size: int,
) -> Mapping[str, Any]:
    collected: list[Any] = []
    current_token = page_token
    current_page_size = page_size
    while True:
        data = fetch_page(page_size=current_page_size, page_token=current_token)
        items = data.get("items")
        if isinstance(items, list):
            collected.extend(items)
        if not _has_more(data):
            break
        current_token = _next_page_token(data)
        if not current_token:
            break
        current_page_size = _normalize_page_size(current_page_size, default=default_page_size)
    return {"all": True, "has_more": False, "count": len(collected), "items": collected}


def _cmd_bitable_create_from_csv(args: argparse.Namespace) -> Mapping[str, Any]:
    service = BitableService(_build_client(args))
    app_token, app_url = service.create_from_csv(
        _require_non_empty_string_arg(args.csv_path, name="csv_path"),
        _require_non_empty_string_arg(args.app_name, name="app-name"),
        _require_non_empty_string_arg(args.table_name, name="table-name"),
    )
    granted = False
    member_id = getattr(args, "grant_member_id", None)
    if member_id:
        service.grant_edit_permission(
            app_token,
            _resolve_member_identity(
                args,
                member_id=member_id,
                member_id_type=getattr(args, "member_id_type", None),
            ),
            str(args.member_id_type),
        )
        granted = True
    return {"app_token": app_token, "app_url": app_url, "granted": granted}


def _cmd_bitable_create_table(args: argparse.Namespace) -> Mapping[str, Any]:
    table = _parse_json_object(
        json_text=getattr(args, "table_json", None),
        file_path=getattr(args, "table_file", None),
        stdin_enabled=bool(getattr(args, "table_stdin", False)),
        name="table",
        required=True,
    )
    service = BitableService(_build_client(args))
    return service.create_table(
        _require_non_empty_string_arg(args.app_token, name="app-token"),
        table,
    )


def _cmd_bitable_create_record(args: argparse.Namespace) -> Mapping[str, Any]:
    fields = _parse_json_object(
        json_text=getattr(args, "fields_json", None),
        file_path=getattr(args, "fields_file", None),
        stdin_enabled=bool(getattr(args, "fields_stdin", False)),
        name="fields",
        required=True,
    )
    service = BitableService(_build_client(args))
    app_token = _require_non_empty_string_arg(args.app_token, name="app-token")
    return service.create_record(
        app_token,
        _resolve_bitable_table_id(
            service,
            app_token,
            table_id=getattr(args, "table_id", None),
            command_name="create-record",
        ),
        fields,
        user_id_type=getattr(args, "user_id_type", None),
        client_token=getattr(args, "client_token", None),
        ignore_consistency_check=bool(getattr(args, "ignore_consistency_check", False)),
    )


def _cmd_bitable_list_records(args: argparse.Namespace) -> Mapping[str, Any]:
    service = BitableService(_build_client(args))
    app_token = _require_non_empty_string_arg(args.app_token, name="app-token")
    table_id = _resolve_bitable_table_id(
        service,
        app_token,
        table_id=getattr(args, "table_id", None),
        command_name="list-records",
    )
    page_size = getattr(args, "page_size", None)
    page_token = getattr(args, "page_token", None)
    view_id = getattr(args, "view_id", None)
    user_id_type = getattr(args, "user_id_type", None)
    filter_expr = getattr(args, "filter", None)
    sort = getattr(args, "sort", None)
    field_names = getattr(args, "field_names", None)
    text_field_as_array = _optional_bool(getattr(args, "text_field_as_array", None))
    if not bool(getattr(args, "all", False)):
        return service.list_records(
            app_token,
            table_id,
            page_size=page_size,
            page_token=page_token,
            view_id=view_id,
            user_id_type=user_id_type,
            filter=filter_expr,
            sort=sort,
            field_names=field_names,
            text_field_as_array=text_field_as_array,
        )

    return _collect_all_pages(
        lambda *, page_size, page_token: service.list_records(
            app_token,
            table_id,
            page_size=page_size,
            page_token=page_token,
            view_id=view_id,
            user_id_type=user_id_type,
            filter=filter_expr,
            sort=sort,
            field_names=field_names,
            text_field_as_array=text_field_as_array,
        ),
        page_size=page_size,
        page_token=page_token,
        default_page_size=500,
    )


def _cmd_bitable_grant_edit(args: argparse.Namespace) -> Mapping[str, bool]:
    service = BitableService(_build_client(args))
    service.grant_edit_permission(
        _require_non_empty_string_arg(args.app_token, name="app-token"),
        _resolve_member_identity(
            args,
            member_id=getattr(args, "member_id", None),
            member_id_type=getattr(args, "member_id_type", None),
        ),
        str(args.member_id_type),
    )
    return {"ok": True}


def _cmd_bitable_get_app(args: argparse.Namespace) -> Mapping[str, Any]:
    service = BitableService(_build_client(args))
    return _augment_bitable_app_result(
        service,
        service.get_app(_require_non_empty_string_arg(args.app_token, name="app-token")),
    )


def _cmd_bitable_update_app(args: argparse.Namespace) -> Mapping[str, Any]:
    service = BitableService(_build_client(args))
    return service.update_app(
        _require_non_empty_string_arg(args.app_token, name="app-token"),
        name=getattr(args, "name", None),
    )


def _cmd_bitable_list_tables(args: argparse.Namespace) -> Mapping[str, Any]:
    service = BitableService(_build_client(args))
    app_token = _require_non_empty_string_arg(args.app_token, name="app-token")
    page_size = getattr(args, "page_size", None)
    page_token = getattr(args, "page_token", None)
    if not bool(getattr(args, "all", False)):
        return service.list_tables(app_token, page_size=page_size, page_token=page_token)
    return _collect_all_pages(
        lambda *, page_size, page_token: service.list_tables(
            app_token,
            page_size=page_size,
            page_token=page_token,
        ),
        page_size=page_size,
        page_token=page_token,
        default_page_size=100,
    )


def _cmd_bitable_copy_app(args: argparse.Namespace) -> Mapping[str, Any]:
    service = BitableService(_build_client(args))
    return _augment_bitable_app_result(
        service,
        service.copy_app(
            _require_non_empty_string_arg(args.app_token, name="app-token"),
            name=getattr(args, "name", None),
            folder_token=getattr(args, "folder_token", None),
        ),
    )


def _cmd_bitable_list_views(args: argparse.Namespace) -> Mapping[str, Any]:
    service = BitableService(_build_client(args))
    app_token = _require_non_empty_string_arg(args.app_token, name="app-token")
    table_id = _resolve_bitable_table_id(
        service,
        app_token,
        table_id=getattr(args, "table_id", None),
        command_name="list-views",
    )
    page_size = getattr(args, "page_size", None)
    page_token = getattr(args, "page_token", None)
    if not bool(getattr(args, "all", False)):
        return service.list_views(app_token, table_id, page_size=page_size, page_token=page_token)
    return _collect_all_pages(
        lambda *, page_size, page_token: service.list_views(
            app_token,
            table_id,
            page_size=page_size,
            page_token=page_token,
        ),
        page_size=page_size,
        page_token=page_token,
        default_page_size=100,
    )


def _cmd_bitable_get_view(args: argparse.Namespace) -> Mapping[str, Any]:
    service = BitableService(_build_client(args))
    app_token = _require_non_empty_string_arg(args.app_token, name="app-token")
    return service.get_view(
        app_token,
        _resolve_bitable_table_id(
            service,
            app_token,
            table_id=getattr(args, "table_id", None),
            command_name="get-view",
        ),
        _require_non_empty_string_arg(args.view_id, name="view-id"),
    )


def _cmd_bitable_create_view(args: argparse.Namespace) -> Mapping[str, Any]:
    view: dict[str, object] = {
        "view_name": _require_non_empty_string_arg(args.view_name, name="view-name")
    }
    view_type = getattr(args, "view_type", None)
    if view_type:
        view["view_type"] = str(view_type)
    service = BitableService(_build_client(args))
    app_token = _require_non_empty_string_arg(args.app_token, name="app-token")
    return service.create_view(
        app_token,
        _resolve_bitable_table_id(
            service,
            app_token,
            table_id=getattr(args, "table_id", None),
            command_name="create-view",
        ),
        view,
    )


def _cmd_bitable_update_view(args: argparse.Namespace) -> Mapping[str, Any]:
    service = BitableService(_build_client(args))
    app_token = _require_non_empty_string_arg(args.app_token, name="app-token")
    return service.update_view(
        app_token,
        _resolve_bitable_table_id(
            service,
            app_token,
            table_id=getattr(args, "table_id", None),
            command_name="update-view",
        ),
        _require_non_empty_string_arg(args.view_id, name="view-id"),
        {"view_name": _require_non_empty_string_arg(args.view_name, name="view-name")},
    )


def _cmd_bitable_delete_view(args: argparse.Namespace) -> Mapping[str, Any]:
    service = BitableService(_build_client(args))
    app_token = _require_non_empty_string_arg(args.app_token, name="app-token")
    return service.delete_view(
        app_token,
        _resolve_bitable_table_id(
            service,
            app_token,
            table_id=getattr(args, "table_id", None),
            command_name="delete-view",
        ),
        _require_non_empty_string_arg(args.view_id, name="view-id"),
    )


def _cmd_bitable_get_field(args: argparse.Namespace) -> Mapping[str, Any]:
    service = BitableService(_build_client(args))
    app_token = _require_non_empty_string_arg(args.app_token, name="app-token")
    return service.get_field(
        app_token,
        _resolve_bitable_table_id(
            service,
            app_token,
            table_id=getattr(args, "table_id", None),
            command_name="get-field",
        ),
        _require_non_empty_string_arg(args.field_id, name="field-id"),
    )


def _cmd_docx_create(args: argparse.Namespace) -> Mapping[str, Any]:
    service = DocxService(_build_client(args))
    return service.create_document(
        str(args.title),
        folder_token=getattr(args, "folder_token", None),
    )


def _cmd_docx_get(args: argparse.Namespace) -> Mapping[str, Any]:
    service = DocxDocumentService(_build_client(args))
    return service.get_document(str(args.document_id))


def _cmd_docx_raw_content(args: argparse.Namespace) -> Mapping[str, Any]:
    service = DocxDocumentService(_build_client(args))
    data = service.get_raw_content(
        str(args.document_id),
        lang=getattr(args, "lang", None),
    )
    output = getattr(args, "output", None)
    if not output:
        return data
    content = data.get("content")
    if not isinstance(content, str):
        raise ValueError("docx raw-content response does not contain string content")
    output_path = _write_text_output(str(output), content)
    return {"ok": True, "output": str(output_path), "size": len(content)}


def _cmd_docx_get_content(args: argparse.Namespace) -> Mapping[str, Any]:
    service = DocContentService(_build_client(args))
    data = service.get_content(
        str(args.doc_token),
        doc_type=str(args.doc_type),
        content_type=str(args.content_type),
        lang=getattr(args, "lang", None),
    )
    output = getattr(args, "output", None)
    if not output:
        return data
    content = data.get("content")
    if not isinstance(content, str):
        raise ValueError("docs content response does not contain string content")
    output_path = _write_text_output(str(output), content)
    return {"ok": True, "output": str(output_path), "size": len(content)}


def _cmd_docx_list_blocks(args: argparse.Namespace) -> Mapping[str, Any]:
    service = DocxDocumentService(_build_client(args))
    document_id = str(args.document_id)
    page_size = getattr(args, "page_size", None)
    page_token = getattr(args, "page_token", None)
    document_revision_id = getattr(args, "document_revision_id", None)
    user_id_type = getattr(args, "user_id_type", None)
    if not bool(getattr(args, "all", False)):
        return service.list_blocks(
            document_id,
            page_size=page_size,
            page_token=page_token,
            document_revision_id=document_revision_id,
            user_id_type=user_id_type,
        )
    return _collect_all_pages(
        lambda *, page_size, page_token: service.list_blocks(
            document_id,
            page_size=page_size,
            page_token=page_token,
            document_revision_id=document_revision_id,
            user_id_type=user_id_type,
        ),
        page_size=page_size,
        page_token=page_token,
        default_page_size=500,
    )


def _cmd_docx_get_block(args: argparse.Namespace) -> Mapping[str, Any]:
    service = DocxBlockService(_build_client(args))
    return service.get_block(
        str(args.document_id),
        str(args.block_id),
        document_revision_id=getattr(args, "document_revision_id", None),
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_docx_list_children(args: argparse.Namespace) -> Mapping[str, Any]:
    service = DocxBlockService(_build_client(args))
    document_id = str(args.document_id)
    block_id = str(args.block_id)
    page_size = getattr(args, "page_size", None)
    page_token = getattr(args, "page_token", None)
    document_revision_id = getattr(args, "document_revision_id", None)
    with_descendants = _optional_bool(getattr(args, "with_descendants", None))
    user_id_type = getattr(args, "user_id_type", None)
    if not bool(getattr(args, "all", False)):
        return service.list_children(
            document_id,
            block_id,
            page_size=page_size,
            page_token=page_token,
            document_revision_id=document_revision_id,
            with_descendants=with_descendants,
            user_id_type=user_id_type,
        )
    return _collect_all_pages(
        lambda *, page_size, page_token: service.list_children(
            document_id,
            block_id,
            page_size=page_size,
            page_token=page_token,
            document_revision_id=document_revision_id,
            with_descendants=with_descendants,
            user_id_type=user_id_type,
        ),
        page_size=page_size,
        page_token=page_token,
        default_page_size=500,
    )


def _cmd_docx_create_children(args: argparse.Namespace) -> Mapping[str, Any]:
    children = _parse_json_array(
        json_text=getattr(args, "children_json", None),
        file_path=getattr(args, "children_file", None),
        stdin_enabled=bool(getattr(args, "children_stdin", False)),
        name="children",
        required=True,
    )
    service = DocxBlockService(_build_client(args))
    return service.create_children(
        str(args.document_id),
        str(args.block_id),
        children=children,
        index=int(args.index),
        document_revision_id=getattr(args, "document_revision_id", None),
        client_token=getattr(args, "client_token", None),
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_docx_create_descendant(args: argparse.Namespace) -> Mapping[str, Any]:
    children_id = _string_list(
        _parse_json_array(
            json_text=getattr(args, "children_id_json", None),
            file_path=getattr(args, "children_id_file", None),
            stdin_enabled=bool(getattr(args, "children_id_stdin", False)),
            name="children_id",
            required=True,
        ),
        name="children_id",
    )
    descendants = _parse_json_array(
        json_text=getattr(args, "descendants_json", None),
        file_path=getattr(args, "descendants_file", None),
        stdin_enabled=bool(getattr(args, "descendants_stdin", False)),
        name="descendants",
        required=True,
    )
    service = DocxBlockService(_build_client(args))
    return service.create_descendant(
        str(args.document_id),
        str(args.block_id),
        children_id=children_id,
        descendants=descendants,
        index=int(args.index),
        document_revision_id=getattr(args, "document_revision_id", None),
        client_token=getattr(args, "client_token", None),
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_docx_update_block(args: argparse.Namespace) -> Mapping[str, Any]:
    operations = _parse_json_object(
        json_text=getattr(args, "operations_json", None),
        file_path=getattr(args, "operations_file", None),
        stdin_enabled=bool(getattr(args, "operations_stdin", False)),
        name="operations",
        required=True,
    )
    service = DocxBlockService(_build_client(args))
    return service.update_block(
        str(args.document_id),
        str(args.block_id),
        operations=operations,
        document_revision_id=getattr(args, "document_revision_id", None),
        client_token=getattr(args, "client_token", None),
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_docx_batch_update(args: argparse.Namespace) -> Mapping[str, Any]:
    requests = _parse_json_array(
        json_text=getattr(args, "requests_json", None),
        file_path=getattr(args, "requests_file", None),
        stdin_enabled=bool(getattr(args, "requests_stdin", False)),
        name="requests",
        required=True,
    )
    service = DocxBlockService(_build_client(args))
    return service.batch_update(
        str(args.document_id),
        requests=requests,
        document_revision_id=getattr(args, "document_revision_id", None),
        client_token=getattr(args, "client_token", None),
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_docx_delete_children_range(args: argparse.Namespace) -> Mapping[str, Any]:
    service = DocxBlockService(_build_client(args))
    return service.delete_children_range(
        str(args.document_id),
        str(args.block_id),
        start_index=int(args.start_index),
        end_index=int(args.end_index),
        document_revision_id=getattr(args, "document_revision_id", None),
        client_token=getattr(args, "client_token", None),
    )


def _cmd_docx_convert_content(args: argparse.Namespace) -> Mapping[str, Any]:
    content = _resolve_text_input(
        text=getattr(args, "content", None),
        file_path=getattr(args, "content_file", None),
        stdin_enabled=bool(getattr(args, "content_stdin", False)),
        name="content",
    )
    service = DocxBlockService(_build_client(args))
    data = service.convert_content(content, content_type=str(args.content_type))
    output = getattr(args, "output", None)
    if not output:
        return data
    output_path = _write_json_output(str(output), data)
    return {"ok": True, "output": str(output_path)}


def _cmd_docx_insert_content(args: argparse.Namespace) -> Mapping[str, Any]:
    content = _resolve_text_input(
        text=getattr(args, "content", None),
        file_path=getattr(args, "content_file", None),
        stdin_enabled=bool(getattr(args, "content_stdin", False)),
        name="content",
    )
    service = DocxService(_build_client(args))
    data = service.insert_content(
        str(args.document_id),
        content,
        block_id=getattr(args, "block_id", None),
        content_type=str(args.content_type),
        index=int(args.index),
        document_revision_id=getattr(args, "document_revision_id", None),
        client_token=getattr(args, "client_token", None),
        user_id_type=getattr(args, "user_id_type", None),
    )
    if bool(getattr(args, "full_response", False)):
        return data
    return _summarize_docx_insert_result(data, content=content)


def _cmd_docx_set_title(args: argparse.Namespace) -> Mapping[str, Any]:
    title = _resolve_text_input(
        text=getattr(args, "text", None),
        file_path=getattr(args, "text_file", None),
        stdin_enabled=bool(getattr(args, "text_stdin", False)),
        name="text",
    )
    service = DocxService(_build_client(args))
    return service.set_title(
        str(args.document_id),
        title,
        document_revision_id=getattr(args, "document_revision_id", None),
        client_token=getattr(args, "client_token", None),
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_docx_set_block_text(args: argparse.Namespace) -> Mapping[str, Any]:
    text = _resolve_text_input(
        text=getattr(args, "text", None),
        file_path=getattr(args, "text_file", None),
        stdin_enabled=bool(getattr(args, "text_stdin", False)),
        name="text",
    )
    service = DocxService(_build_client(args))
    return service.set_block_text(
        str(args.document_id),
        str(args.block_id),
        text,
        document_revision_id=getattr(args, "document_revision_id", None),
        client_token=getattr(args, "client_token", None),
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_docx_replace_image(args: argparse.Namespace) -> Mapping[str, Any]:
    service = DocxService(_build_client(args))
    return service.replace_image(
        str(args.document_id),
        str(args.block_id),
        file_path=str(args.path),
        file_name=getattr(args, "file_name", None),
        checksum=getattr(args, "checksum", None),
        content_type=getattr(args, "content_type", None),
        document_revision_id=getattr(args, "document_revision_id", None),
        client_token=getattr(args, "client_token", None),
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_docx_replace_file(args: argparse.Namespace) -> Mapping[str, Any]:
    service = DocxService(_build_client(args))
    return service.replace_file(
        str(args.document_id),
        str(args.block_id),
        file_path=str(args.path),
        file_name=getattr(args, "file_name", None),
        checksum=getattr(args, "checksum", None),
        content_type=getattr(args, "content_type", None),
        document_revision_id=getattr(args, "document_revision_id", None),
        client_token=getattr(args, "client_token", None),
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_docx_grant_edit(args: argparse.Namespace) -> Mapping[str, bool]:
    service = DocxService(_build_client(args))
    service.grant_edit_permission(
        str(args.document_id),
        _resolve_member_identity(
            args,
            member_id=getattr(args, "member_id", None),
            member_id_type=getattr(args, "member_id_type", None),
        ),
        str(args.member_id_type),
    )
    return {"ok": True}


def _cmd_drive_upload_file(args: argparse.Namespace) -> Mapping[str, Any]:
    service = DriveFileService(_build_client(args))
    return service.upload_file(
        str(args.path),
        parent_type=str(args.parent_type),
        parent_node=str(args.parent_node),
        file_name=getattr(args, "file_name", None),
        checksum=getattr(args, "checksum", None),
        content_type=getattr(args, "content_type", None),
    )


def _cmd_drive_download_file(args: argparse.Namespace) -> Mapping[str, Any]:
    service = DriveFileService(_build_client(args))
    content = service.download_file(str(args.file_token))
    output_path = _write_bytes_output(str(args.output), content)
    return {"ok": True, "output": str(output_path), "size": len(content)}


def _cmd_drive_meta(args: argparse.Namespace) -> Mapping[str, Any]:
    request_docs = _parse_json_array(
        json_text=getattr(args, "request_docs_json", None),
        file_path=getattr(args, "request_docs_file", None),
        stdin_enabled=bool(getattr(args, "request_docs_stdin", False)),
        name="request_docs",
        required=True,
    )
    service = DriveFileService(_build_client(args))
    return service.batch_query_metas(
        request_docs,
        with_url=_optional_bool(getattr(args, "with_url", None)),
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_drive_stats(args: argparse.Namespace) -> Mapping[str, Any]:
    service = DriveFileService(_build_client(args))
    return service.get_file_statistics(
        str(args.file_token),
        file_type=str(args.file_type),
    )


def _cmd_drive_view_records(args: argparse.Namespace) -> Mapping[str, Any]:
    service = DriveFileService(_build_client(args))
    file_token = str(args.file_token)
    file_type = str(args.file_type)
    page_size: int = args.page_size
    page_token = getattr(args, "page_token", None)
    viewer_id_type = getattr(args, "viewer_id_type", None)
    if not bool(getattr(args, "all", False)):
        return service.list_file_view_records(
            file_token,
            file_type=file_type,
            page_size=int(page_size),
            page_token=page_token,
            viewer_id_type=viewer_id_type,
        )
    return _collect_all_pages(
        lambda *, page_size, page_token: service.list_file_view_records(
            file_token,
            file_type=file_type,
            page_size=int(_normalize_page_size(page_size, default=200)),
            page_token=page_token,
            viewer_id_type=viewer_id_type,
        ),
        page_size=page_size,
        page_token=page_token,
        default_page_size=200,
    )


def _cmd_drive_copy(args: argparse.Namespace) -> Mapping[str, Any]:
    extra = _parse_json_object(
        json_text=getattr(args, "extra_json", None),
        file_path=getattr(args, "extra_file", None),
        stdin_enabled=bool(getattr(args, "extra_stdin", False)),
        name="extra",
        required=False,
    )
    service = DriveFileService(_build_client(args))
    return service.copy_file(
        str(args.file_token),
        name=str(args.name),
        folder_token=str(args.folder_token),
        type=getattr(args, "type", None),
        extra=extra or None,
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_drive_move(args: argparse.Namespace) -> Mapping[str, Any]:
    service = DriveFileService(_build_client(args))
    return service.move_file(
        str(args.file_token),
        type=getattr(args, "type", None),
        folder_token=getattr(args, "folder_token", None),
    )


def _cmd_drive_delete(args: argparse.Namespace) -> Mapping[str, Any]:
    service = DriveFileService(_build_client(args))
    return service.delete_file(
        str(args.file_token),
        type=str(args.type),
    )


def _cmd_drive_shortcut(args: argparse.Namespace) -> Mapping[str, Any]:
    service = DriveFileService(_build_client(args))
    return service.create_shortcut(
        parent_token=str(args.parent_token),
        refer_token=str(args.refer_token),
        refer_type=str(args.refer_type),
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_drive_create_import_task(args: argparse.Namespace) -> Mapping[str, Any]:
    task = _parse_json_object(
        json_text=getattr(args, "task_json", None),
        file_path=getattr(args, "task_file", None),
        stdin_enabled=bool(getattr(args, "task_stdin", False)),
        name="task",
        required=True,
    )
    service = DriveFileService(_build_client(args))
    return service.create_import_task(task)


def _cmd_drive_get_import_task(args: argparse.Namespace) -> Mapping[str, Any]:
    service = DriveFileService(_build_client(args))
    return service.get_import_task(str(args.ticket))


def _cmd_drive_create_export_task(args: argparse.Namespace) -> Mapping[str, Any]:
    task = _parse_json_object(
        json_text=getattr(args, "task_json", None),
        file_path=getattr(args, "task_file", None),
        stdin_enabled=bool(getattr(args, "task_stdin", False)),
        name="task",
        required=True,
    )
    service = DriveFileService(_build_client(args))
    return service.create_export_task(task)


def _cmd_drive_get_export_task(args: argparse.Namespace) -> Mapping[str, Any]:
    service = DriveFileService(_build_client(args))
    return service.get_export_task(str(args.ticket), token=getattr(args, "token", None))


def _cmd_drive_download_export_file(args: argparse.Namespace) -> Mapping[str, Any]:
    service = DriveFileService(_build_client(args))
    content = service.download_export_file(str(args.file_token))
    output_path = _write_bytes_output(str(args.output), content)
    return {"ok": True, "output": str(output_path), "size": len(content)}


def _cmd_drive_version_create(args: argparse.Namespace) -> Mapping[str, Any]:
    service = DriveFileService(_build_client(args))
    return service.create_version(
        str(args.file_token),
        name=str(args.name),
        obj_type=str(args.obj_type),
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_drive_version_list(args: argparse.Namespace) -> Mapping[str, Any]:
    service = DriveFileService(_build_client(args))
    file_token = str(args.file_token)
    obj_type = str(args.obj_type)
    page_size: int = args.page_size
    page_token = getattr(args, "page_token", None)
    user_id_type = getattr(args, "user_id_type", None)
    if not bool(getattr(args, "all", False)):
        return service.list_versions(
            file_token,
            obj_type=obj_type,
            page_size=int(page_size),
            page_token=page_token,
            user_id_type=user_id_type,
        )
    return _collect_all_pages(
        lambda *, page_size, page_token: service.list_versions(
            file_token,
            obj_type=obj_type,
            page_size=int(_normalize_page_size(page_size, default=200)),
            page_token=page_token,
            user_id_type=user_id_type,
        ),
        page_size=page_size,
        page_token=page_token,
        default_page_size=200,
    )


def _cmd_drive_version_get(args: argparse.Namespace) -> Mapping[str, Any]:
    service = DriveFileService(_build_client(args))
    return service.get_version(
        str(args.file_token),
        str(args.version_id),
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_drive_version_delete(args: argparse.Namespace) -> Mapping[str, Any]:
    service = DriveFileService(_build_client(args))
    return service.delete_version(
        str(args.file_token),
        str(args.version_id),
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_drive_grant_edit(args: argparse.Namespace) -> Mapping[str, bool]:
    service = DrivePermissionService(_build_client(args))
    service.grant_edit_permission(
        str(args.token),
        _resolve_member_identity(
            args,
            member_id=getattr(args, "member_id", None),
            member_id_type=getattr(args, "member_id_type", None),
        ),
        str(args.member_id_type),
        resource_type=str(args.resource_type),
        permission=str(args.permission),
    )
    return {"ok": True}


def _cmd_drive_list_members(args: argparse.Namespace) -> Mapping[str, Any]:
    service = DrivePermissionService(_build_client(args))
    return service.list_members(
        str(args.token),
        resource_type=str(args.resource_type),
        fields=getattr(args, "fields", None),
        perm_type=getattr(args, "perm_type", None),
    )


def _cmd_drive_list_files(args: argparse.Namespace) -> Mapping[str, Any]:
    service = DriveFileService(_build_client(args))
    page_size = getattr(args, "page_size", None)
    page_token = getattr(args, "page_token", None)
    folder_token = getattr(args, "folder_token", None)
    order_by = getattr(args, "order_by", None)
    direction = getattr(args, "direction", None)
    user_id_type = getattr(args, "user_id_type", None)
    if not bool(getattr(args, "all", False)):
        return service.list_files(
            folder_token=folder_token,
            page_size=page_size,
            page_token=page_token,
            order_by=order_by,
            direction=direction,
            user_id_type=user_id_type,
        )

    collected: list[Any] = []
    current_token = page_token
    while True:
        data = service.list_files(
            folder_token=folder_token,
            page_size=page_size,
            page_token=current_token,
            order_by=order_by,
            direction=direction,
            user_id_type=user_id_type,
        )
        files = data.get("files")
        if isinstance(files, list):
            collected.extend(files)
        if not _has_more(data):
            break
        current_token = _next_page_token(data)
        if not current_token:
            break
    return {"all": True, "has_more": False, "count": len(collected), "files": collected}


def _cmd_drive_create_folder(args: argparse.Namespace) -> Mapping[str, Any]:
    service = DriveFileService(_build_client(args))
    return service.create_folder(name=str(args.name), folder_token=str(args.folder_token))


def _cmd_wiki_list_spaces(args: argparse.Namespace) -> Mapping[str, Any]:
    service = WikiService(_build_client(args))
    page_size = getattr(args, "page_size", None)
    page_token = getattr(args, "page_token", None)
    if not bool(getattr(args, "all", False)):
        return service.list_spaces(
            page_size=page_size,
            page_token=page_token,
        )

    return _collect_all_pages(
        lambda *, page_size, page_token: service.list_spaces(
            page_size=page_size,
            page_token=page_token,
        ),
        page_size=page_size,
        page_token=page_token,
        default_page_size=20,
    )


def _cmd_wiki_search_nodes(args: argparse.Namespace) -> Mapping[str, Any]:
    service = WikiService(_build_client(args))
    query = str(args.query)
    space_id = getattr(args, "space_id", None)
    node_id = getattr(args, "node_id", None)
    page_size = getattr(args, "page_size", None)
    page_token = getattr(args, "page_token", None)
    if not bool(getattr(args, "all", False)):
        return service.search_nodes(
            query,
            space_id=space_id,
            node_id=node_id,
            page_size=page_size,
            page_token=page_token,
        )

    return _collect_all_pages(
        lambda *, page_size, page_token: service.search_nodes(
            query,
            space_id=space_id,
            node_id=node_id,
            page_size=page_size,
            page_token=page_token,
        ),
        page_size=page_size,
        page_token=page_token,
        default_page_size=20,
    )


def _cmd_wiki_get_node(args: argparse.Namespace) -> Mapping[str, Any]:
    service = WikiService(_build_client(args))
    return service.get_node(str(args.token), obj_type=getattr(args, "obj_type", None))


def _cmd_wiki_list_nodes(args: argparse.Namespace) -> Mapping[str, Any]:
    service = WikiService(_build_client(args))
    space_id = str(args.space_id)
    parent_node_token = getattr(args, "parent_node_token", None)
    page_size = getattr(args, "page_size", None)
    page_token = getattr(args, "page_token", None)
    if not bool(getattr(args, "all", False)):
        return service.list_nodes(
            space_id,
            parent_node_token=parent_node_token,
            page_size=page_size,
            page_token=page_token,
        )

    return _collect_all_pages(
        lambda *, page_size, page_token: service.list_nodes(
            space_id,
            parent_node_token=parent_node_token,
            page_size=page_size,
            page_token=page_token,
        ),
        page_size=page_size,
        page_token=page_token,
        default_page_size=50,
    )


__all__ = [name for name in globals() if name.startswith("_cmd_")]
