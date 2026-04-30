from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import parse_qs, quote, urlparse

from ..runtime import _build_client, infer_mime_type, read_value


def _data(response: Mapping[str, Any]) -> dict[str, Any]:
    payload = response.get("data")
    if isinstance(payload, Mapping):
        return {str(key): value for key, value in payload.items()}
    return {}


def _optional_string(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _split_csv(value: Any) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _json_value(value: Any, *, default: Any = None) -> Any:
    text = _optional_string(value)
    if text is None:
        return default
    try:
        return json.loads(read_value(text))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON value: {text}") from exc


def _json_object(value: Any) -> dict[str, Any]:
    parsed = _json_value(value, default={})
    if not isinstance(parsed, Mapping):
        raise ValueError("expected a JSON object")
    return {str(key): item for key, item in parsed.items()}


def _json_array(value: Any, *, default: list[Any] | None = None) -> list[Any]:
    parsed = _json_value(value, default=[] if default is None else default)
    if not isinstance(parsed, list):
        raise ValueError("expected a JSON array")
    return parsed


def _spreadsheet_token(args: argparse.Namespace) -> str:
    token = _optional_string(getattr(args, "spreadsheet_token", None))
    if token:
        return token
    url = _optional_string(getattr(args, "url", None))
    if not url:
        raise ValueError("specify --spreadsheet-token or --url")
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    for key in ("spreadsheet_token", "token"):
        value = query.get(key, [""])[0].strip()
        if value:
            return value
    parts = [part for part in parsed.path.split("/") if part]
    for part in reversed(parts):
        if part.startswith(("sht", "shtcn", "base")):
            return part
    return parts[-1] if parts else url


def _sheet_id(args: argparse.Namespace) -> str:
    sheet_id = _optional_string(getattr(args, "sheet_id", None))
    if not sheet_id:
        raise ValueError("specify --sheet-id")
    return sheet_id


def _first_sheet_id(spreadsheet: Mapping[str, Any], data: Mapping[str, Any]) -> str:
    candidates = (
        spreadsheet.get("sheets"),
        spreadsheet.get("sheet_list"),
        data.get("sheets"),
        data.get("sheet_list"),
    )
    for candidate in candidates:
        if not isinstance(candidate, list):
            continue
        for item in candidate:
            if not isinstance(item, Mapping):
                continue
            properties = item.get("properties")
            properties_map = properties if isinstance(properties, Mapping) else {}
            sheet_id = _optional_string(
                item.get("sheet_id")
                or item.get("sheetId")
                or properties_map.get("sheet_id")
                or properties_map.get("sheetId")
            )
            if sheet_id:
                return sheet_id
    return ""


def _query_first_sheet_id(client: Any, token: str) -> str:
    data = _data(client.request_json("GET", f"/sheets/v3/spreadsheets/{quote(token, safe='')}/sheets/query"))
    candidates = (data.get("sheets"), data.get("sheet_list"))
    for candidate in candidates:
        if not isinstance(candidate, list):
            continue
        for item in candidate:
            if not isinstance(item, Mapping):
                continue
            properties = item.get("properties")
            properties_map = properties if isinstance(properties, Mapping) else {}
            sheet_id = _optional_string(
                item.get("sheet_id")
                or item.get("sheetId")
                or properties_map.get("sheet_id")
                or properties_map.get("sheetId")
            )
            if sheet_id:
                return sheet_id
    return "Sheet1"


def _sheet_range(args: argparse.Namespace, *, default_to_sheet: bool = False) -> str:
    range_value = _optional_string(getattr(args, "range", None))
    sheet_id = _optional_string(getattr(args, "sheet_id", None))
    if range_value and "!" not in range_value and sheet_id:
        return _normalize_point_range(f"{sheet_id}!{range_value}")
    if range_value:
        return _normalize_point_range(range_value)
    if default_to_sheet and sheet_id:
        return sheet_id
    raise ValueError("specify --range or --sheet-id")


_SINGLE_CELL_RE = re.compile(r"^[A-Za-z]+[1-9][0-9]*$")


def _normalize_point_range(value: str) -> str:
    if "!" not in value:
        return value
    sheet_id, sub_range = value.split("!", 1)
    if ":" in sub_range or not _SINGLE_CELL_RE.fullmatch(sub_range):
        return value
    return f"{sheet_id}!{sub_range}:{sub_range}"


def _values_payload(args: argparse.Namespace) -> dict[str, Any]:
    values = _json_array(getattr(args, "values", None))
    return {"range": _sheet_range(args, default_to_sheet=True), "values": values}


def _media_upload(client: Any, file_path: str, *, parent_node: str, parent_type: str = "sheet_image") -> dict[str, Any]:
    content = Path(file_path).read_bytes()
    file_name = os.path.basename(file_path)
    return _data(
        client.request_multipart(
            "POST",
            "/drive/v1/medias/upload_all",
            data={
                "file_name": file_name,
                "parent_type": parent_type,
                "parent_node": parent_node,
                "size": len(content),
            },
            files={"file": (file_name, content, infer_mime_type(file_path))},
        )
    )


def _cmd_sheets_shortcut(args: argparse.Namespace) -> Mapping[str, Any]:
    command = str(getattr(args, "sheets_command", "") or "").strip()
    client = _build_client(args)
    token = None
    if command not in {"create"}:
        token = _spreadsheet_token(args)

    if command == "info":
        info = _data(client.request_json("GET", f"/sheets/v3/spreadsheets/{quote(str(token), safe='')}"))
        try:
            sheets = _data(client.request_json("GET", f"/sheets/v3/spreadsheets/{quote(str(token), safe='')}/sheets/query"))
        except Exception:
            sheets = {}
        return {"spreadsheet": info, "sheets": sheets or None}

    if command == "read":
        read_range = _sheet_range(args, default_to_sheet=True)
        params: dict[str, Any] = {}
        render = _optional_string(getattr(args, "value_render_option", None))
        if render:
            params["valueRenderOption"] = render
        return _data(
            client.request_json(
                "GET",
                f"/sheets/v2/spreadsheets/{quote(str(token), safe='')}/values/{quote(read_range, safe='')}",
                params=params or None,
            )
        )

    if command == "write":
        return _data(
            client.request_json(
                "PUT",
                f"/sheets/v2/spreadsheets/{quote(str(token), safe='')}/values",
                payload={"valueRange": _values_payload(args)},
            )
        )

    if command == "append":
        return _data(
            client.request_json(
                "POST",
                f"/sheets/v2/spreadsheets/{quote(str(token), safe='')}/values_append",
                payload={"valueRange": _values_payload(args)},
            )
        )

    if command == "create":
        body = {"title": str(getattr(args, "title", "") or "Untitled spreadsheet")}
        folder_token = _optional_string(getattr(args, "folder_token", None))
        if folder_token:
            body["folder_token"] = folder_token
        data = _data(client.request_json("POST", "/sheets/v3/spreadsheets", payload=body))
        spreadsheet_raw = data.get("spreadsheet")
        spreadsheet: Mapping[str, Any] = spreadsheet_raw if isinstance(spreadsheet_raw, Mapping) else {}
        created_token = str(spreadsheet.get("spreadsheet_token") or data.get("spreadsheet_token") or "")
        initial_sheet_id = _first_sheet_id(spreadsheet, data)
        rows: list[Any] = []
        headers = _json_array(getattr(args, "headers", None), default=[])
        if headers:
            rows.append(headers)
        rows.extend(_json_array(getattr(args, "data", None), default=[]))
        if created_token and rows:
            if not initial_sheet_id:
                initial_sheet_id = _query_first_sheet_id(client, created_token)
            client.request_json(
                "POST",
                f"/sheets/v2/spreadsheets/{quote(created_token, safe='')}/values_append",
                payload={"valueRange": {"range": initial_sheet_id, "values": rows}},
            )
        return {
            "spreadsheet_token": created_token,
            "sheet_id": initial_sheet_id,
            "title": body["title"],
            "url": spreadsheet.get("url"),
            "rows_appended": len(rows),
        }

    if command == "find":
        return _data(
            client.request_json(
                "POST",
                f"/sheets/v3/spreadsheets/{quote(str(token), safe='')}/sheets/{quote(_sheet_id(args), safe='')}/find",
                payload={"find": str(getattr(args, "find", "") or ""), "find_condition": _json_object(getattr(args, "condition", None))},
            )
        )

    if command in {"merge-cells", "unmerge-cells"}:
        endpoint = "merge_cells" if command == "merge-cells" else "unmerge_cells"
        body: dict[str, Any] = {"range": _sheet_range(args)}
        merge_type = _optional_string(getattr(args, "merge_type", None))
        if merge_type:
            body["mergeType"] = merge_type
        return _data(client.request_json("POST", f"/sheets/v2/spreadsheets/{quote(str(token), safe='')}/{endpoint}", payload=body))

    if command == "replace":
        return _data(
            client.request_json(
                "POST",
                f"/sheets/v3/spreadsheets/{quote(str(token), safe='')}/sheets/{quote(_sheet_id(args), safe='')}/replace",
                payload={"find": str(getattr(args, "find", "") or ""), "replacement": str(getattr(args, "replacement", "") or "")},
            )
        )

    if command in {"set-style", "batch-set-style"}:
        if command == "batch-set-style":
            styles = _json_array(
                getattr(args, "data", None) or getattr(args, "styles", None),
                default=[],
            )
            if not styles:
                style = _json_object(getattr(args, "style", None))
                styles = [{"ranges": [_sheet_range(args)], "style": style}]
            body = {"data": _normalize_batch_styles(styles)}
            path = f"/sheets/v2/spreadsheets/{quote(str(token), safe='')}/styles_batch_update"
        else:
            style = _json_object(getattr(args, "style", None))
            body = {"appendStyle": {"range": _sheet_range(args), "style": style}}
            path = f"/sheets/v2/spreadsheets/{quote(str(token), safe='')}/style"
        return _data(client.request_json("PUT", path, payload=body))

    if command in {"add-dimension", "insert-dimension", "update-dimension", "move-dimension", "delete-dimension"}:
        return _handle_dimension(client, args, token=str(token), command=command)

    if command.endswith("filter-view") or "filter-view-" in command or command == "list-filter-views":
        return _handle_filter_view(client, args, token=str(token), command=command)

    if "dropdown" in command:
        return _handle_dropdown(client, args, token=str(token), command=command)

    if command in {"media-upload", "write-image"}:
        file_path = str(getattr(args, "file", "") or "")
        if not file_path:
            raise ValueError("specify --file")
        parent_node = _optional_string(getattr(args, "parent_node", None)) or _sheet_id(args)
        upload = _media_upload(client, file_path, parent_node=parent_node)
        return {"file_token": upload.get("file_token"), "file_name": os.path.basename(file_path), "parent_node": parent_node}

    if "float-image" in command:
        return _handle_float_image(client, args, token=str(token), command=command)

    if command == "export":
        return _data(
            client.request_json(
                "POST",
                "/drive/v1/export_tasks",
                payload={"token": str(token), "type": "sheet", "file_extension": str(getattr(args, "file_extension", "") or "xlsx")},
            )
        )

    raise ValueError(f"unsupported sheets shortcut: {command}")


def _handle_filter_view(client: Any, args: argparse.Namespace, *, token: str, command: str) -> Mapping[str, Any]:
    sheet_id = _sheet_id(args)
    base = f"/sheets/v3/spreadsheets/{quote(token, safe='')}/sheets/{quote(sheet_id, safe='')}/filter_views"
    filter_view_id = _optional_string(getattr(args, "filter_view_id", None))
    condition_id = _optional_string(getattr(args, "condition_id", None))
    if command == "list-filter-views":
        return _data(client.request_json("GET", f"{base}/query"))
    if command == "get-filter-view":
        return _data(client.request_json("GET", f"{base}/{quote(str(filter_view_id), safe='')}"))
    if command == "delete-filter-view":
        return _data(client.request_json("DELETE", f"{base}/{quote(str(filter_view_id), safe='')}"))
    if command in {"create-filter-view", "update-filter-view"}:
        body = {"range": _sheet_range(args)}
        if name := _optional_string(getattr(args, "filter_view_name", None) or getattr(args, "name", None)):
            body["filter_view_name"] = name
        method = "POST" if command == "create-filter-view" else "PATCH"
        path = base if command == "create-filter-view" else f"{base}/{quote(str(filter_view_id), safe='')}"
        return _data(client.request_json(method, path, payload=body))
    conditions = f"{base}/{quote(str(filter_view_id), safe='')}/conditions"
    if command == "list-filter-view-conditions":
        return _data(client.request_json("GET", conditions))
    if command == "get-filter-view-condition":
        return _data(client.request_json("GET", f"{conditions}/{quote(str(condition_id), safe='')}"))
    if command == "delete-filter-view-condition":
        return _data(client.request_json("DELETE", f"{conditions}/{quote(str(condition_id), safe='')}"))
    body = {
        "condition": {
            "field_index": int(getattr(args, "field_index", 0) or 0),
            "filter_type": str(getattr(args, "filter_type", "") or "text"),
            "compare_type": str(getattr(args, "compare_type", "") or "equal"),
            "expected": _split_csv(getattr(args, "expected", None)),
        }
    }
    method = "POST" if command == "create-filter-view-condition" else "PATCH"
    path = conditions if command == "create-filter-view-condition" else f"{conditions}/{quote(str(condition_id), safe='')}"
    return _data(client.request_json(method, path, payload=body))


def _handle_dropdown(client: Any, args: argparse.Namespace, *, token: str, command: str) -> Mapping[str, Any]:
    base = f"/sheets/v2/spreadsheets/{quote(token, safe='')}/dataValidation"
    if command == "get-dropdown":
        data_range = _sheet_range(args)
        return _data(client.request_json("GET", base, params={"range": data_range, "dataValidationType": "list"}))
    if command == "delete-dropdown":
        ranges = _json_array(getattr(args, "ranges", None), default=[])
        if not ranges and (data_range := _optional_string(getattr(args, "range", None))):
            ranges = [data_range]
        body = {"dataValidationRanges": [{"range": _normalize_point_range(str(item))} for item in ranges]}
        return _data(client.request_json("DELETE", base, payload=body))
    values = _json_array(getattr(args, "condition_values", None) or getattr(args, "options", None))
    validation: dict[str, Any] = {"conditionValues": values}
    options: dict[str, Any] = {}
    if getattr(args, "multiple", None) is not None:
        options["multipleValues"] = bool(getattr(args, "multiple"))
    if getattr(args, "highlight", None) is not None:
        options["highlightValidData"] = bool(getattr(args, "highlight"))
    colors = _json_array(getattr(args, "colors", None), default=[])
    if colors:
        options["colors"] = colors
    if options:
        validation["options"] = options
    if command == "set-dropdown":
        body = {
            "range": _sheet_range(args),
            "dataValidationType": "list",
            "dataValidation": validation,
        }
        return _data(client.request_json("POST", base, payload=body))
    ranges = _json_array(getattr(args, "ranges", None), default=[])
    if not ranges and (data_range := _optional_string(getattr(args, "range", None))):
        ranges = [data_range]
    sheet_id = _sheet_id(args)
    body = {
        "ranges": [_normalize_point_range(str(item)) for item in ranges],
        "dataValidationType": "list",
        "dataValidation": validation,
    }
    path = f"{base}/{quote(str(sheet_id), safe='')}"
    return _data(client.request_json("PUT", path, payload=body))


def _handle_float_image(client: Any, args: argparse.Namespace, *, token: str, command: str) -> Mapping[str, Any]:
    sheet_id = _sheet_id(args)
    base = f"/sheets/v3/spreadsheets/{quote(token, safe='')}/sheets/{quote(sheet_id, safe='')}/float_images"
    image_id = _optional_string(getattr(args, "float_image_id", None)) or _optional_string(getattr(args, "image_id", None))
    if command == "list-float-images":
        return _data(client.request_json("GET", f"{base}/query"))
    if command == "get-float-image":
        return _data(client.request_json("GET", f"{base}/{quote(str(image_id), safe='')}"))
    if command == "delete-float-image":
        return _data(client.request_json("DELETE", f"{base}/{quote(str(image_id), safe='')}"))
    body = {
        "float_image_token": str(getattr(args, "float_image_token", "") or getattr(args, "file_token", "") or ""),
        "range": _optional_string(getattr(args, "range", None)) or "",
    }
    for attr in ("width", "height", "offset_x", "offset_y"):
        value = getattr(args, attr, None)
        if value is not None:
            body[attr] = int(value)
    method = "POST" if command == "create-float-image" else "PATCH"
    path = base if command == "create-float-image" else f"{base}/{quote(str(image_id), safe='')}"
    return _data(client.request_json(method, path, payload=body))


def _normalize_batch_styles(styles: list[Any]) -> list[Any]:
    normalized: list[Any] = []
    for item in styles:
        if not isinstance(item, Mapping):
            normalized.append(item)
            continue
        entry = {str(key): value for key, value in item.items()}
        if isinstance(entry.get("ranges"), list):
            entry["ranges"] = [_normalize_point_range(str(value)) for value in entry["ranges"]]
        elif "range" in entry:
            entry["ranges"] = [_normalize_point_range(str(entry.pop("range")))]
        normalized.append(entry)
    return normalized


def _handle_dimension(client: Any, args: argparse.Namespace, *, token: str, command: str) -> Mapping[str, Any]:
    dimension = str(getattr(args, "dimension", "") or "ROWS")
    sheet_id = _sheet_id(args)
    encoded_token = quote(str(token), safe="")
    if command == "add-dimension":
        body = {"dimension": {"sheetId": sheet_id, "majorDimension": dimension, "length": int(getattr(args, "length", 0) or 0)}}
        return _data(client.request_json("POST", f"/sheets/v2/spreadsheets/{encoded_token}/dimension_range", payload=body))
    if command == "insert-dimension":
        body = {
            "dimension": {
                "sheetId": sheet_id,
                "majorDimension": dimension,
                "startIndex": int(getattr(args, "start_index", 0) or 0),
                "endIndex": int(getattr(args, "end_index", 0) or 0),
            }
        }
        if inherit_style := _optional_string(getattr(args, "inherit_style", None)):
            body["inheritStyle"] = inherit_style
        return _data(client.request_json("POST", f"/sheets/v2/spreadsheets/{encoded_token}/insert_dimension_range", payload=body))
    if command == "update-dimension":
        props: dict[str, Any] = {}
        if getattr(args, "visible", None) is not None:
            props["visible"] = bool(getattr(args, "visible"))
        if getattr(args, "fixed_size", None) is not None:
            props["fixedSize"] = int(getattr(args, "fixed_size"))
        body = {
            "dimension": {
                "sheetId": sheet_id,
                "majorDimension": dimension,
                "startIndex": int(getattr(args, "start_index", 0) or 0),
                "endIndex": int(getattr(args, "end_index", 0) or 0),
            },
            "dimensionProperties": props,
        }
        return _data(client.request_json("PUT", f"/sheets/v2/spreadsheets/{encoded_token}/dimension_range", payload=body))
    if command == "move-dimension":
        source_end = getattr(args, "end_index", None)
        if source_end is None and getattr(args, "length", None) is not None:
            source_end = int(getattr(args, "source_index", getattr(args, "start_index", 0)) or 0) + int(getattr(args, "length") or 0) - 1
        source_index = getattr(args, "source_index", None)
        if source_index is None:
            source_index = getattr(args, "start_index", 0)
        body = {
            "source": {
                "major_dimension": dimension,
                "start_index": int(source_index or 0),
                "end_index": int(source_end if source_end is not None else getattr(args, "end_index", 0) or 0),
            },
            "destination_index": int(getattr(args, "destination_index", 0) or 0),
        }
        return _data(client.request_json("POST", f"/sheets/v3/spreadsheets/{encoded_token}/sheets/{quote(sheet_id, safe='')}/move_dimension", payload=body))
    if command == "delete-dimension":
        body = {
            "dimension": {
                "sheetId": sheet_id,
                "majorDimension": dimension,
                "startIndex": int(getattr(args, "start_index", 0) or 0),
                "endIndex": int(getattr(args, "end_index", 0) or 0),
            }
        }
        return _data(client.request_json("DELETE", f"/sheets/v2/spreadsheets/{encoded_token}/dimension_range", payload=body))
    raise ValueError(f"unsupported dimension shortcut: {command}")


__all__ = ["_cmd_sheets_shortcut"]
