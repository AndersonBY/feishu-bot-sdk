from __future__ import annotations

import dataclasses
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping, Optional

from ...exceptions import HTTPRequestError

def _print_result(result: Any, *, output_format: str) -> None:
    normalized = _to_jsonable(result)
    if output_format == "json":
        print(json.dumps(normalized, ensure_ascii=False, indent=2))
        return
    _print_human(normalized)


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


def _print_error(message: str, *, exit_code: int, output_format: str) -> int:
    if output_format == "json":
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": message,
                    "exit_code": exit_code,
                },
                ensure_ascii=False,
            )
        )
    else:
        print(f"Error: {message}", file=sys.stderr)
    return exit_code


def _format_http_error(exc: HTTPRequestError) -> str:
    parts = [str(exc)]
    if exc.status_code is not None:
        parts.append(f"status_code={exc.status_code}")
    if exc.response_text:
        parts.append(f"response={exc.response_text[:500]}")
        response_lower = exc.response_text.lower()
        if '"code":20029' in response_lower or "redirect_uri" in response_lower and "illegal" in response_lower:
            parts.append(
                "hint=oauth redirect_uri is invalid; configure exact redirect URL in "
                "Feishu console: Development Config -> Security -> Redirect URL."
            )
        if '"code":193107' in response_lower or "no permission to access attachment file token" in response_lower:
            parts.append(
                "hint=calendar attachments require media upload with "
                "parent_type='calendar' and parent_node='<calendar_id>'; "
                "prefer `feishu calendar attach-material`."
            )
        if '"code":234001' in response_lower and "invalid request param" in response_lower:
            parts.append(
                "hint=invalid request parameters. For IM image/file resources from received messages, "
                "use message resource download with message_id, for example: "
                "`feishu media download-file <resource_key> <output> --message-id <om_xxx> --resource-type image|file --auth-mode tenant`."
            )
        if '"code":99991668' in response_lower and "user access token not support" in response_lower:
            parts.append(
                "hint=this endpoint does not support user access token; "
                "retry with tenant auth: `--auth-mode tenant` (or provide app_id/app_secret)."
            )
        if '"code":99991679' in response_lower or "required one of these privileges under the user identity" in response_lower:
            scope_hint = _extract_required_user_scopes(exc.response_text)
            if scope_hint:
                parts.append(
                    "hint=missing user scopes; re-authorize with:\n"
                    f"feishu auth login --scope \"offline_access {scope_hint}\" --format json"
                )
            else:
                parts.append(
                    "hint=missing user scope; run `feishu auth login --scope \"offline_access <required_scope>\"` "
                    "and retry."
                )
        if '"code":99991663' in response_lower or '"code":99991668' in response_lower:
            parts.append(
                "hint=invalid access token; prefer user auth for search APIs: "
                "`feishu auth login --scope \"offline_access search:app search:message search:docs:read\" --format json`"
            )
        if '"code":234008' in response_lower or "not the resource sender" in response_lower:
            parts.append(
                "hint=resource belongs to a message sender. For user-sent image/file, use message resource download: "
                "`feishu media download-file <resource_key> <output> --message-id <om_xxx> --resource-type image|file`."
            )
    return "; ".join(parts)


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


def _format_feishu_error_message(message: str) -> str:
    lower = message.lower()
    parts = [message]
    if "code': 20005" in lower or '"code": 20005' in lower or "invalid access token" in lower:
        parts.append(
            "hint=user access token is invalid or expired; re-login with:\n"
            "feishu auth login --scope \"offline_access search:app search:message search:docs:read\" --format json"
        )
    if "code': 20026" in lower or '"code": 20026' in lower or "refresh token is invalid" in lower:
        parts.append(
            "hint=refresh token is invalid/rotated; run `feishu auth login` again, "
            "or clear FEISHU_USER_REFRESH_TOKEN to use static user access token only."
        )
    return "; ".join(parts)


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
