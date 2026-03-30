from __future__ import annotations

import dataclasses
import csv
import io
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping, Optional, cast

from ...exceptions import HTTPRequestError

_DEFAULT_MAX_OUTPUT_CHARS = 25000
_PREVIEW_LIST_ITEM_OPTIONS = (20, 10, 5, 2, 1)
_PREVIEW_MAPPING_ITEM_OPTIONS = (40, 20, 10, 5)
_PREVIEW_STRING_CHAR_OPTIONS = (4000, 2000, 1000, 500, 200, 80)
_PREVIEW_MAX_DEPTH = 6
_MAX_TRUNCATION_NOTES = 8
_ERROR_CODE_PATTERN = re.compile(r"""["']code["']\s*[:=]\s*["']?(\d+)["']?""")


def _print_result(
    result: Any,
    *,
    output_format: str,
    max_output_chars: Any = None,
    output_offset: Any = None,
    full_output: bool = False,
    save_output: Any = None,
    cli_args: Any = None,
) -> None:
    normalized = _to_jsonable(result)
    output_format = _normalize_output_format(output_format)
    max_output_chars_value = _normalize_output_char_limit(max_output_chars)
    output_offset_value = _normalize_output_offset(output_offset)
    if full_output and output_offset_value:
        raise ValueError("output-offset cannot be combined with --full-output")
    save_output_path = _resolve_output_path(save_output)
    if save_output_path is not None:
        _write_json_file(save_output_path, normalized)
    if output_format in {"table", "csv", "ndjson"}:
        _print_structured(normalized, output_format=output_format)
        return
    prepared = _prepare_regular_output(
        normalized,
        max_output_chars=max_output_chars_value,
        output_offset=output_offset_value,
        full_output=full_output,
        save_output_path=save_output_path,
        cli_args=cli_args,
    )
    if output_format == "json":
        sys.stdout.write(_serialize_json(prepared))
        return
    _print_human(prepared)


def _print_human(result: Any) -> None:
    if result is None:
        print("OK")
        return
    if isinstance(result, Mapping):
        mapping = {str(key): value for key, value in result.items()}
        if not mapping:
            print("OK")
            return
        if _is_flat_mapping(mapping):
            width = max(len(key) for key in mapping)
            for key in sorted(mapping):
                print(f"{key:<{width}} : {mapping[key]}")
            return
        print(json.dumps(mapping, ensure_ascii=False, indent=2))
        return
    if isinstance(result, list):
        if not result:
            print("[]")
            return
        for index, item in enumerate(result, start=1):
            print(f"{index}. {item}")
        return
    print(result)


def _print_structured(result: Any, *, output_format: str) -> None:
    rows = _normalize_rows(result)
    if output_format == "ndjson":
        for row in rows:
            print(json.dumps(_to_jsonable(row), ensure_ascii=False))
        return
    if not rows:
        print("")
        return
    fieldnames = _collect_fieldnames(rows)
    if output_format == "csv":
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: _stringify_scalar(row.get(name)) for name in fieldnames})
        sys.stdout.write(buffer.getvalue())
        return
    widths = {name: len(name) for name in fieldnames}
    string_rows: list[dict[str, str]] = []
    for row in rows:
        rendered = {name: _stringify_scalar(row.get(name)) for name in fieldnames}
        string_rows.append(rendered)
        for name, value in rendered.items():
            widths[name] = max(widths[name], len(value))
    header = "  ".join(name.ljust(widths[name]) for name in fieldnames)
    divider = "  ".join("-" * widths[name] for name in fieldnames)
    print(header)
    print(divider)
    for row in string_rows:
        print("  ".join(row[name].ljust(widths[name]) for name in fieldnames))


def _normalize_rows(result: Any) -> list[dict[str, Any]]:
    if isinstance(result, list):
        return [_row_to_mapping(item) for item in result]
    if isinstance(result, Mapping):
        items = result.get("items")
        if isinstance(items, list):
            return [_row_to_mapping(item) for item in items]
        return [_row_to_mapping(result)]
    return [{"value": result}]


def _row_to_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return {str(key): item for key, item in value.items()}
    return {"value": value}


def _collect_fieldnames(rows: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for row in rows:
        for key in row:
            if key not in names:
                names.append(key)
    return names


def _stringify_scalar(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(_to_jsonable(value), ensure_ascii=False)
    return str(value)


def _normalize_output_format(value: str) -> str:
    normalized = str(value or "").strip().lower() or "json"
    if normalized == "human":
        return "pretty"
    return normalized


def _build_event_view(ctx: Any, *, include_payload: bool) -> Mapping[str, Any]:
    envelope = getattr(ctx, "envelope", None)
    payload = getattr(ctx, "payload", {})
    event = getattr(ctx, "event", {})
    result: dict[str, Any] = {
        "event_type": str(getattr(envelope, "event_type", "")),
        "event_id": getattr(envelope, "event_id", None),
    }
    sender_open_id = _extract_nested_value(
        event,
        ["sender", "sender_id", "open_id"],
    )
    message_id = _extract_nested_value(
        event,
        ["message", "message_id"],
    )
    chat_id = _extract_nested_value(
        event,
        ["message", "chat_id"],
    )
    if isinstance(sender_open_id, str) and sender_open_id:
        result["sender_open_id"] = sender_open_id
    if isinstance(message_id, str) and message_id:
        result["message_id"] = message_id
    if isinstance(chat_id, str) and chat_id:
        result["chat_id"] = chat_id
    if include_payload:
        result["payload"] = payload
    return result


def _extract_nested_value(source: Any, path: list[str]) -> Any:
    current = source
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _emit_event(event: Mapping[str, Any], *, output_format: str, output_file: Path | None) -> None:
    _print_stream_event(event, output_format=output_format)
    if output_file is not None:
        _append_jsonl(output_file, event)


def _print_stream_event(event: Mapping[str, Any], *, output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(_to_jsonable(event), ensure_ascii=False))
        return
    event_type = event.get("event_type")
    event_id = event.get("event_id")
    print(f"[event] type={event_type} id={event_id}")
    if "payload" in event:
        print(json.dumps(_to_jsonable(event.get("payload")), ensure_ascii=False, indent=2))


def _append_jsonl(path: Path, event: Mapping[str, Any]) -> None:
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(_to_jsonable(event), ensure_ascii=False))
        file.write("\n")


def _print_runtime_status(payload: Mapping[str, Any], *, output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(_to_jsonable(payload), ensure_ascii=False))
        return
    status = payload.get("status")
    if status == "listening":
        print(f"Listening on http://{payload.get('host')}:{payload.get('port')}{payload.get('path')}")
        return
    if status == "stopped":
        print(f"Server stopped. requests={payload.get('requests')}")
        return
    print(json.dumps(_to_jsonable(payload), ensure_ascii=False))


def _print_runtime_error(message: str, *, output_format: str) -> None:
    if output_format == "json":
        print(json.dumps({"error": message}, ensure_ascii=False))
    else:
        print(f"Runtime error: {message}", file=sys.stderr)


def _print_error(
    error: str | Mapping[str, Any],
    *,
    exit_code: int,
    output_format: str,
    error_type: str | None = None,
) -> int:
    detail = _coerce_error_detail(error, exit_code=exit_code, error_type=error_type)
    if output_format == "json":
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": detail,
                    "exit_code": exit_code,
                },
                ensure_ascii=False,
            )
        )
    else:
        print(f"Error: {_render_error_message(detail)}", file=sys.stderr)
    return exit_code


def _format_http_error(exc: HTTPRequestError) -> str:
    return _render_error_message(_build_http_error_detail(exc))


def _extract_required_user_scopes(response_text: str) -> str:
    match = re.search(
        r"required one of these privileges under the user identity:\s*\[([^\]]+)\]",
        response_text,
        flags=re.IGNORECASE,
    )
    if match is None:
        return ""
    raw_scopes = [item.strip() for item in match.group(1).split(",")]
    scopes: list[str] = []
    for scope in raw_scopes:
        if not scope:
            continue
        if scope not in scopes:
            scopes.append(scope)
    return " ".join(scopes)


def _extract_required_tenant_scopes(response_text: str) -> str:
    match = re.search(
        r"one of the following scopes is required:\s*\[([^\]]+)\]",
        response_text,
        flags=re.IGNORECASE,
    )
    if match is None:
        return ""
    raw_scopes = [item.strip() for item in match.group(1).split(",")]
    scopes: list[str] = []
    for scope in raw_scopes:
        if not scope:
            continue
        if scope not in scopes:
            scopes.append(scope)
    return " ".join(scopes)


def _format_configuration_error_message(message: str) -> str:
    return _render_error_message(_build_configuration_error_detail(message))


def _format_feishu_error_message(message: str) -> str:
    return _render_error_message(_build_feishu_error_detail(message))


def _build_http_error_detail(exc: HTTPRequestError) -> dict[str, Any]:
    response_text = exc.response_text or ""
    hint = _http_error_hint(response_text)
    detail = _build_error_detail(
        error_type="http_error",
        code=_extract_error_code(response_text) or "http_request_failed",
        message=str(exc),
        hint=hint,
        retryable=_is_retryable_http_status(exc.status_code),
    )
    if exc.status_code is not None:
        detail["status_code"] = exc.status_code
    if response_text:
        detail["response_excerpt"] = response_text[:500]
    return detail


def _build_configuration_error_detail(message: str) -> dict[str, Any]:
    lower = message.lower()
    hint: str | None = None
    if "user mode requires user_access_token/access_token or user_refresh_token" in lower:
        hint = (
            "user auth is unavailable. In a v-claw managed session, run "
            "`vclawctl auth current --provider feishu`; if "
            "`capabilities.requester_auth_available=false`, do not retry user-mode "
            "commands and re-authorize requester access from v-claw settings. "
            "Otherwise provide `FEISHU_USER_ACCESS_TOKEN`/`FEISHU_USER_REFRESH_TOKEN` "
            "or switch to bot identity."
        )
    elif "auth whoami requires user_access_token/access_token or user_refresh_token" in lower:
        hint = (
            "user identity lookup requires requester auth. In a v-claw managed "
            "session, confirm `requester_auth_available=true` before calling "
            "`feishu auth whoami`."
        )
    return _build_error_detail(
        error_type="configuration_error",
        code="configuration_error",
        message=message,
        hint=hint,
        retryable=False,
    )


def _build_feishu_error_detail(message: str) -> dict[str, Any]:
    lower = message.lower()
    hint: str | None = None
    if "code': 20005" in lower or '"code": 20005' in lower or "invalid access token" in lower:
        hint = (
            "user access token is invalid or expired; re-login with:\n"
            "feishu auth login --scope \"offline_access search:app search:message search:docs:read\" --format json"
        )
    elif "code': 20026" in lower or '"code": 20026' in lower or "refresh token is invalid" in lower:
        hint = (
            "refresh token is invalid/rotated; run `feishu auth login` again, "
            "or clear FEISHU_USER_REFRESH_TOKEN to use static user access token only."
        )
    return _build_error_detail(
        error_type="feishu_error",
        code=_extract_error_code(message) or "feishu_api_error",
        message=message,
        hint=hint,
        retryable=False,
    )


def _build_error_detail(
    *,
    error_type: str,
    code: Any,
    message: str,
    hint: str | None,
    retryable: bool,
) -> dict[str, Any]:
    return {
        "type": error_type,
        "code": code,
        "message": message,
        "hint": hint,
        "retryable": retryable,
    }


def _coerce_error_detail(
    error: str | Mapping[str, Any],
    *,
    exit_code: int,
    error_type: str | None,
) -> dict[str, Any]:
    if isinstance(error, Mapping):
        err = cast(Mapping[str, Any], error)
        detail = _build_error_detail(
            error_type=str(err.get("type") or error_type or _default_error_type(exit_code)),
            code=err.get("code") if "code" in err else _default_error_code(error_type, exit_code),
            message=str(err.get("message") or err.get("error") or ""),
            hint=_optional_text(err.get("hint")),
            retryable=bool(err.get("retryable", False)),
        )
        for key in ("status_code", "response_excerpt"):
            if key in err:
                detail[key] = err[key]
        if "details" in err:
            detail["details"] = _to_jsonable(err.get("details"))
        return detail
    return _build_error_detail(
        error_type=error_type or _default_error_type(exit_code),
        code=_default_error_code(error_type, exit_code),
        message=str(error),
        hint=None,
        retryable=False,
    )


def _render_error_message(detail: Mapping[str, Any]) -> str:
    parts = [str(detail.get("message") or "")]
    status_code = detail.get("status_code")
    if status_code is not None:
        parts.append(f"status_code={status_code}")
    response_excerpt = _optional_text(detail.get("response_excerpt"))
    if response_excerpt:
        parts.append(f"response={response_excerpt}")
    hint = _optional_text(detail.get("hint"))
    if hint:
        parts.append(f"hint={hint}")
    return "; ".join(part for part in parts if part)


def _default_error_type(exit_code: int) -> str:
    if exit_code == 2:
        return "usage_error"
    if exit_code == 3:
        return "feishu_error"
    if exit_code == 4:
        return "http_error"
    return "runtime_error"


def _default_error_code(error_type: str | None, exit_code: int) -> str:
    normalized = str(error_type or _default_error_type(exit_code)).strip().lower()
    if normalized in {"usage_error", "validation_error"}:
        return "invalid_input"
    if normalized == "configuration_error":
        return "configuration_error"
    if normalized == "feishu_error":
        return "feishu_api_error"
    if normalized == "http_error":
        return "http_request_failed"
    if normalized == "internal_error":
        return "internal_error"
    return f"exit_{exit_code}"


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _extract_error_code(value: str | None) -> int | str | None:
    text = _optional_text(value)
    if not text:
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, Mapping):
        code = payload.get("code")
        if isinstance(code, bool):
            return None
        if isinstance(code, int):
            return code
        if isinstance(code, float):
            return int(code)
        if isinstance(code, str) and code.strip():
            stripped = code.strip()
            return int(stripped) if stripped.isdigit() else stripped
    match = _ERROR_CODE_PATTERN.search(text)
    if match is None:
        return None
    return int(match.group(1))


def _http_error_hint(response_text: str) -> str | None:
    response_lower = response_text.lower()
    if '"code":20029' in response_lower or "redirect_uri" in response_lower and "illegal" in response_lower:
        return (
            "oauth redirect_uri is invalid; configure exact redirect URL in "
            "Feishu console: Development Config -> Security -> Redirect URL."
        )
    if '"code":193107' in response_lower or "no permission to access attachment file token" in response_lower:
        return (
            "calendar attachments require media upload with "
            "parent_type='calendar' and parent_node='<calendar_id>'; "
            "prefer `feishu calendar attach-material`."
        )
    if '"code":234001' in response_lower and "invalid request param" in response_lower:
        return (
            "invalid request parameters. For IM image/file resources from received messages, "
            "use message resource download with message_id, for example: "
            "`feishu media download-file <resource_key> <output> --message-id <om_xxx> --resource-type image|file`."
        )
    if '"code":99991668' in response_lower and "user access token not support" in response_lower:
        return (
            "this endpoint does not support user access token; "
            "retry with bot identity: `--as bot` (or provide app_id/app_secret)."
        )
    if '"code":99991679' in response_lower or "required one of these privileges under the user identity" in response_lower:
        scope_hint = _extract_required_user_scopes(response_text)
        if scope_hint:
            return (
                "missing user scopes; re-authorize with:\n"
                f"feishu auth login --scope \"offline_access {scope_hint}\" --format json"
            )
        return (
            "missing user scope; run `feishu auth login --scope \"offline_access <required_scope>\"` "
            "and retry."
        )
    if '"code":99991672' in response_lower or "one of the following scopes is required" in response_lower:
        scope_hint = _extract_required_tenant_scopes(response_text)
        if scope_hint:
            return (
                "missing tenant app scopes; enable one of these scopes in the "
                f"Feishu app console and retry: {scope_hint}. This is not fixed by "
                "switching to user auth."
            )
        return (
            "missing tenant app scope; enable the required scope in the "
            "Feishu app console and retry. This is not fixed by switching to user auth."
        )
    if '"code":99991663' in response_lower or '"code":99991668' in response_lower:
        return (
            "invalid access token; prefer user auth for search APIs: "
            "`feishu auth login --scope \"offline_access search:app search:message search:docs:read\" --format json`"
        )
    if '"code":234008' in response_lower or "not the resource sender" in response_lower:
        return (
            "resource belongs to a message sender. For user-sent image/file, use message resource download: "
            "`feishu media download-file <resource_key> <output> --message-id <om_xxx> --resource-type image|file`."
        )
    return None


def _is_retryable_http_status(status_code: int | None) -> bool:
    if status_code is None:
        return False
    return status_code in {408, 409, 429} or 500 <= status_code <= 599


def _is_flat_mapping(mapping: Mapping[str, Any]) -> bool:
    for value in mapping.values():
        if isinstance(value, (dict, list, tuple, set)):
            return False
    return True


def _to_jsonable(value: Any) -> Any:
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return _to_jsonable(to_dict())
    if dataclasses.is_dataclass(value):
        # Avoid dataclasses.asdict deep-copy recursion with SDK wrapper objects (e.g. Struct).
        return {field.name: _to_jsonable(getattr(value, field.name)) for field in dataclasses.fields(value)}
    if isinstance(value, Mapping):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _prepare_regular_output(
    normalized: Any,
    *,
    max_output_chars: int,
    output_offset: int,
    full_output: bool,
    save_output_path: Path | None,
    cli_args: Any,
) -> Any:
    if full_output:
        return normalized
    full_json = _serialize_json(normalized)
    if output_offset:
        return _build_json_slice_payload(
            full_json,
            max_output_chars=max_output_chars,
            output_offset=output_offset,
            save_output_path=save_output_path,
            cli_args=cli_args,
        )
    if len(full_json) <= max_output_chars:
        return normalized
    return _build_preview_payload(
        normalized,
        full_json=full_json,
        max_output_chars=max_output_chars,
        save_output_path=save_output_path,
        cli_args=cli_args,
    )


def _build_preview_payload(
    normalized: Any,
    *,
    full_json: str,
    max_output_chars: int,
    save_output_path: Path | None,
    cli_args: Any,
) -> Any:
    total_json_chars = len(full_json)
    base_meta = {
        "truncated": True,
        "mode": "preview",
        "stdout_char_limit": max_output_chars,
        "total_json_chars": total_json_chars,
        "remaining_json_chars": max(0, total_json_chars - max_output_chars),
        "next_output_offset": max_output_chars if total_json_chars > max_output_chars else None,
        "save_output": str(save_output_path) if save_output_path is not None else None,
        "paging": _extract_paging_info(normalized, cli_args),
    }
    for max_list_items in _PREVIEW_LIST_ITEM_OPTIONS:
        for max_mapping_items in _PREVIEW_MAPPING_ITEM_OPTIONS:
            for max_string_chars in _PREVIEW_STRING_CHAR_OPTIONS:
                notes: list[dict[str, Any]] = []
                preview = _build_preview_value(
                    normalized,
                    path="$",
                    depth=0,
                    max_depth=_PREVIEW_MAX_DEPTH,
                    max_list_items=max_list_items,
                    max_mapping_items=max_mapping_items,
                    max_string_chars=max_string_chars,
                    notes=notes,
                )
                payload = _attach_cli_output_meta(
                    preview,
                    _finalize_cli_output_meta(
                        base_meta,
                        notes=notes,
                        cli_args=cli_args,
                    ),
                )
                if len(_serialize_json(payload)) <= max_output_chars:
                    return payload
    return _build_json_slice_payload(
        full_json,
        max_output_chars=max_output_chars,
        output_offset=0,
        save_output_path=save_output_path,
        cli_args=cli_args,
    )


def _build_json_slice_payload(
    full_json: str,
    *,
    max_output_chars: int,
    output_offset: int,
    save_output_path: Path | None,
    cli_args: Any,
) -> Mapping[str, Any]:
    total_json_chars = len(full_json)
    if output_offset < 0:
        raise ValueError("output-offset must be greater than or equal to 0")
    start = min(output_offset, total_json_chars)
    end = min(total_json_chars, start + max_output_chars)
    while end >= start:
        slice_text = full_json[start:end]
        next_offset = end if end < total_json_chars else None
        remaining = max(0, total_json_chars - end)
        meta = _finalize_cli_output_meta(
            {
                "truncated": remaining > 0 or start > 0,
                "mode": "json_slice",
                "stdout_char_limit": max_output_chars,
                "output_offset": start,
                "returned_json_chars": len(slice_text),
                "total_json_chars": total_json_chars,
                "remaining_json_chars": remaining,
                "next_output_offset": next_offset,
                "save_output": str(save_output_path) if save_output_path is not None else None,
                "paging": None,
            },
            notes=[],
            cli_args=cli_args,
        )
        payload = {
            "json_slice": slice_text,
            "_cli_output": meta,
        }
        if len(_serialize_json(payload)) <= max_output_chars:
            return payload
        if end == start:
            break
        reduction = max(1, (end - start) // 2)
        end -= reduction
    return {
        "json_slice": "",
        "_cli_output": _finalize_cli_output_meta(
            {
                "truncated": True,
                "mode": "json_slice",
                "stdout_char_limit": max_output_chars,
                "output_offset": start,
                "returned_json_chars": 0,
                "total_json_chars": total_json_chars,
                "remaining_json_chars": max(0, total_json_chars - start),
                "next_output_offset": start if start < total_json_chars else None,
                "save_output": str(save_output_path) if save_output_path is not None else None,
                "paging": None,
            },
            notes=[],
            cli_args=cli_args,
        ),
    }


def _build_preview_value(
    value: Any,
    *,
    path: str,
    depth: int,
    max_depth: int,
    max_list_items: int,
    max_mapping_items: int,
    max_string_chars: int,
    notes: list[dict[str, Any]],
) -> Any:
    if depth >= max_depth:
        notes.append({"path": path, "reason": "depth_limited"})
        return "<<truncated: depth limit>>"
    if isinstance(value, Mapping):
        preview: dict[str, Any] = {}
        items = list(value.items())
        for key, item_value in items[:max_mapping_items]:
            key_str = str(key)
            child_path = f"{path}.{key_str}" if path != "$" else f"$.{key_str}"
            preview[key_str] = _build_preview_value(
                item_value,
                path=child_path,
                depth=depth + 1,
                max_depth=max_depth,
                max_list_items=max_list_items,
                max_mapping_items=max_mapping_items,
                max_string_chars=max_string_chars,
                notes=notes,
            )
        omitted = len(items) - len(preview)
        if omitted > 0:
            notes.append({"path": path, "reason": "mapping_items_limited", "omitted": omitted})
        return preview
    if isinstance(value, list):
        preview_list: list[Any] = []
        for index, item in enumerate(value[:max_list_items]):
            child_path = f"{path}[{index}]"
            preview_list.append(
                _build_preview_value(
                    item,
                    path=child_path,
                    depth=depth + 1,
                    max_depth=max_depth,
                    max_list_items=max_list_items,
                    max_mapping_items=max_mapping_items,
                    max_string_chars=max_string_chars,
                    notes=notes,
                )
            )
        omitted = len(value) - len(preview_list)
        if omitted > 0:
            notes.append({"path": path, "reason": "list_items_limited", "omitted": omitted})
        return preview_list
    if isinstance(value, str):
        if len(value) <= max_string_chars:
            return value
        omitted = len(value) - max_string_chars
        notes.append({"path": path, "reason": "string_clipped", "omitted_chars": omitted})
        return value[:max_string_chars] + f"... [truncated {omitted} chars]"
    return value


def _attach_cli_output_meta(preview: Any, meta: Mapping[str, Any]) -> Any:
    if isinstance(preview, Mapping):
        payload = {str(key): value for key, value in preview.items()}
        payload["_cli_output"] = meta
        return payload
    return {
        "result": preview,
        "_cli_output": meta,
    }


def _finalize_cli_output_meta(
    base_meta: Mapping[str, Any],
    *,
    notes: list[dict[str, Any]],
    cli_args: Any,
) -> Mapping[str, Any]:
    meta = {str(key): value for key, value in base_meta.items() if value is not None}
    if notes:
        meta["notes"] = notes[:_MAX_TRUNCATION_NOTES]
    meta["hints"] = _build_output_hints(meta, cli_args)
    return meta


def _build_output_hints(meta: Mapping[str, Any], cli_args: Any) -> list[str]:
    hints: list[str] = []
    save_output = meta.get("save_output")
    if isinstance(save_output, str) and save_output:
        hints.append(f"full normalized JSON was written to {save_output}")
    next_output_offset = meta.get("next_output_offset")
    stdout_char_limit = meta.get("stdout_char_limit")
    if isinstance(next_output_offset, int) and isinstance(stdout_char_limit, int):
        hints.append(
            "rerun with "
            f"--output-offset {next_output_offset} --max-output-chars {stdout_char_limit} --format json "
            "to inspect the next JSON slice"
        )
    if meta.get("truncated"):
        hints.append("rerun with --full-output to disable stdout truncation")
    paging = meta.get("paging")
    if isinstance(paging, Mapping):
        next_page_token = paging.get("next_page_token")
        if isinstance(next_page_token, str) and next_page_token:
            hints.append(f"use --page-token {next_page_token} to fetch the next page")
        if paging.get("all") is True:
            hints.append("avoid --all and use --page-size/--page-token when you need incremental pages")
        elif paging.get("supports_page_size"):
            hints.append("use a smaller --page-size to reduce per-call output volume")
    return hints


def _extract_paging_info(normalized: Any, cli_args: Any) -> Mapping[str, Any] | None:
    has_page_size = hasattr(cli_args, "page_size")
    has_page_token = hasattr(cli_args, "page_token")
    has_all = hasattr(cli_args, "all")
    if not (has_page_size or has_page_token or has_all):
        return None
    paging: dict[str, Any] = {
        "supports_page_size": has_page_size,
        "supports_page_token": has_page_token,
        "all": bool(getattr(cli_args, "all", False)) if has_all else False,
    }
    if has_page_size:
        paging["page_size"] = getattr(cli_args, "page_size", None)
    if has_page_token:
        paging["requested_page_token"] = getattr(cli_args, "page_token", None)
    if isinstance(normalized, Mapping):
        has_more = normalized.get("has_more")
        if isinstance(has_more, bool):
            paging["has_more"] = has_more
        next_page_token = normalized.get("page_token")
        if isinstance(next_page_token, str) and next_page_token:
            paging["next_page_token"] = next_page_token
    return paging


def _serialize_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def _normalize_output_char_limit(value: Any) -> int:
    if value is None:
        return _DEFAULT_MAX_OUTPUT_CHARS
    if not isinstance(value, int):
        raise ValueError("max-output-chars must be an integer")
    if value <= 0:
        raise ValueError("max-output-chars must be greater than 0")
    return value


def _normalize_output_offset(value: Any) -> int:
    if value is None:
        return 0
    if not isinstance(value, int):
        raise ValueError("output-offset must be an integer")
    if value < 0:
        raise ValueError("output-offset must be greater than or equal to 0")
    return value


def _resolve_output_path(path_value: Any) -> Path | None:
    if not path_value:
        return None
    return Path(str(path_value))


def _write_json_file(path: Path, payload: Any) -> None:
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_serialize_json(payload), encoding="utf-8")


def _extract_response_data(value: Any) -> dict[str, Any]:
    payload = _to_jsonable(value)
    if not isinstance(payload, Mapping):
        return {}
    data = payload.get("data")
    if isinstance(data, Mapping):
        return {str(key): inner for key, inner in data.items()}
    return {
        str(key): inner
        for key, inner in payload.items()
        if key not in {"code", "msg"}
    }


def _normalize_calendar_attachments(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    attachments: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        file_token_value = item.get("file_token")
        if not isinstance(file_token_value, str) or not file_token_value:
            continue
        attachment: dict[str, Any] = {"file_token": file_token_value}
        name = item.get("name")
        if isinstance(name, str) and name:
            attachment["name"] = name
        is_deleted = item.get("is_deleted")
        if isinstance(is_deleted, bool):
            attachment["is_deleted"] = is_deleted
        attachments.append(attachment)
    return attachments


def _merge_calendar_attachment(
    attachments: list[dict[str, Any]],
    *,
    file_token: str,
    name: Optional[str],
) -> list[dict[str, Any]]:
    merged = [dict(item) for item in attachments]
    for item in merged:
        if item.get("file_token") != file_token:
            continue
        if isinstance(name, str) and name:
            item["name"] = name
        return merged
    new_item: dict[str, Any] = {"file_token": file_token}
    if isinstance(name, str) and name:
        new_item["name"] = name
    merged.append(new_item)
    return merged


def _system_exit_code(exc: SystemExit) -> int:
    code = exc.code
    if code is None:
        return 0
    if isinstance(code, int):
        return code
    return 1


__all__ = [name for name in globals() if not name.startswith("__")]
