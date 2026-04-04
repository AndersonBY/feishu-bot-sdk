from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, time, timedelta, timezone
from typing import Any, Mapping
from urllib.parse import parse_qs, urlparse

from ...task import TaskService
from ..runtime import _build_client


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_RELATIVE_TIME_RE = re.compile(r"^\+(?P<amount>\d+)(?P<unit>[mhdw])$")


def _optional_string(value: Any) -> str | None:
    text = str(value or "").strip()
    if text:
        return text
    return None


def _require_json_object(value: Any, *, flag_name: str) -> dict[str, Any]:
    text = _optional_string(value)
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{flag_name} must be valid JSON: {exc}") from exc
    if not isinstance(parsed, Mapping):
        raise ValueError(f"{flag_name} must be a JSON object")
    return {str(key): item for key, item in parsed.items()}


def _resolve_tasklist_guid(value: str) -> str:
    text = value.strip()
    if text.startswith(("http://", "https://")):
        parsed = urlparse(text)
        guid = parse_qs(parsed.query).get("guid", [""])[0].strip()
        if guid:
            return guid
    return text


def _local_now() -> datetime:
    return datetime.now().astimezone()


def _ensure_tz(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value
    return value.replace(tzinfo=_local_now().tzinfo)


def _start_of_day(value: datetime) -> datetime:
    value = _ensure_tz(value)
    return datetime.combine(value.date(), time(0, 0), tzinfo=value.tzinfo)


def _end_of_day(value: datetime) -> datetime:
    value = _ensure_tz(value)
    return datetime.combine(value.date(), time(23, 59, 59, 999000), tzinfo=value.tzinfo)


def _parse_time_value(raw_value: str, *, upper_bound: bool = False) -> tuple[datetime, bool]:
    value = raw_value.strip()
    if not value:
        raise ValueError("time value is required")
    if value.startswith("date:"):
        value = value[5:].strip()

    if value.isdigit():
        numeric = int(value)
        timestamp_seconds = numeric / 1000 if numeric >= 10**12 else numeric
        return datetime.fromtimestamp(timestamp_seconds, tz=timezone.utc).astimezone(), False

    match = _RELATIVE_TIME_RE.match(value)
    if match:
        amount = int(match.group("amount"))
        unit = match.group("unit")
        base = _local_now()
        if unit == "m":
            return base + timedelta(minutes=amount), False
        if unit == "h":
            return base + timedelta(hours=amount), False
        delta = timedelta(days=amount * 7 if unit == "w" else amount)
        target = base + delta
        return (_end_of_day(target) if upper_bound else _start_of_day(target)), True

    if _DATE_RE.match(value):
        target = datetime.fromisoformat(value)
        target = target.replace(tzinfo=_local_now().tzinfo)
        return (_end_of_day(target) if upper_bound else _start_of_day(target)), True

    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"unsupported time format: {raw_value}") from exc
    return _ensure_tz(parsed), False


def _task_due_payload(value: str) -> dict[str, Any]:
    parsed, is_all_day = _parse_time_value(value, upper_bound=False)
    return {
        "timestamp": str(int(parsed.timestamp() * 1000)),
        "is_all_day": is_all_day,
    }


def _filter_time_ms(value: str, *, upper_bound: bool = False) -> int:
    parsed, _is_all_day = _parse_time_value(value, upper_bound=upper_bound)
    return int(parsed.timestamp() * 1000)


def _task_mapping(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    task = payload.get("task")
    if isinstance(task, Mapping):
        return task
    return {}


def _normalize_task_payload(payload: Mapping[str, Any], **extra: Any) -> dict[str, Any]:
    result = dict(payload)
    task = _task_mapping(payload)
    if task:
        guid = _optional_string(task.get("guid"))
        summary = _optional_string(task.get("summary"))
        url = _optional_string(task.get("url"))
        if guid is not None:
            result.setdefault("guid", guid)
        if summary is not None:
            result.setdefault("summary", summary)
        if url is not None:
            result.setdefault("url", url)
    result.update(extra)
    return result


def _timestamp_to_iso(value: Any) -> str | None:
    raw = _optional_string(value)
    if not raw:
        return None
    try:
        numeric = int(raw)
    except ValueError:
        return None
    return datetime.fromtimestamp(numeric / 1000, tz=timezone.utc).astimezone().isoformat(timespec="seconds")


def _task_member_payload(member_ids: list[str], *, role: str) -> list[dict[str, str]]:
    return [{"id": member_id, "role": role, "type": "user"} for member_id in member_ids]


def _split_member_ids(value: Any) -> list[str]:
    parts = [item.strip() for item in str(value or "").split(",")]
    return [item for item in parts if item]


def _member_ids_by_role(task: Mapping[str, Any], *, role: str) -> list[str]:
    members = task.get("members")
    if not isinstance(members, list):
        return []
    output: list[str] = []
    for item in members:
        if not isinstance(item, Mapping):
            continue
        if str(item.get("role") or "") != role:
            continue
        member_id = _optional_string(item.get("id"))
        if member_id:
            output.append(member_id)
    return output


def _task_is_completed(task: Mapping[str, Any]) -> bool:
    value = task.get("completed_at")
    if value in (None, "", 0, "0"):
        return False
    return True


def _task_reminder_ids(task: Mapping[str, Any]) -> list[str]:
    reminders = task.get("reminders")
    if not isinstance(reminders, list):
        return []
    output: list[str] = []
    for item in reminders:
        if not isinstance(item, Mapping):
            continue
        reminder_id = _optional_string(item.get("id"))
        if reminder_id:
            output.append(reminder_id)
    return output


def _parse_relative_fire_minutes(value: str) -> int:
    text = value.strip().lower()
    if not text:
        raise ValueError("reminder value is required")
    if text.endswith("m"):
        minutes = int(text[:-1])
    elif text.endswith("h"):
        minutes = int(text[:-1]) * 60
    elif text.endswith("d"):
        minutes = int(text[:-1]) * 24 * 60
    elif text.endswith("w"):
        minutes = int(text[:-1]) * 7 * 24 * 60
    else:
        minutes = int(text)
    if minutes < 0:
        raise ValueError("reminder minutes must be >= 0")
    return minutes


def _build_task_create_payload(args: argparse.Namespace) -> dict[str, Any]:
    payload = _require_json_object(getattr(args, "data", None), flag_name="--data")

    summary = _optional_string(getattr(args, "summary", None))
    if summary is not None:
        payload["summary"] = summary

    description = _optional_string(getattr(args, "description", None))
    if description is not None:
        payload["description"] = description

    assignee = _optional_string(getattr(args, "assignee", None))
    if assignee is not None:
        payload["members"] = _task_member_payload([assignee], role="assignee")

    due = _optional_string(getattr(args, "due", None))
    if due is not None:
        payload["due"] = _task_due_payload(due)

    tasklist_id = _optional_string(getattr(args, "tasklist_id", None))
    if tasklist_id is not None:
        payload["tasklists"] = [{"tasklist_guid": _resolve_tasklist_guid(tasklist_id)}]

    idempotency_key = _optional_string(getattr(args, "idempotency_key", None))
    if idempotency_key is not None:
        payload["client_token"] = idempotency_key

    if not _optional_string(payload.get("summary")):
        raise ValueError("task summary is required; pass --summary or include it inside --data")

    return payload


def _normalize_task_item(task: Mapping[str, Any]) -> dict[str, Any]:
    due_at = None
    due = task.get("due")
    if isinstance(due, Mapping):
        due_at = _timestamp_to_iso(due.get("timestamp"))
    item = {
        "guid": _optional_string(task.get("guid")),
        "summary": _optional_string(task.get("summary")),
        "url": _optional_string(task.get("url")),
        "created_at": _timestamp_to_iso(task.get("created_at")),
        "due_at": due_at,
        "completed_at": _timestamp_to_iso(task.get("completed_at")),
    }
    return {key: value for key, value in item.items() if value is not None}


def _fetch_task_pages(
    service: TaskService,
    *,
    completed: bool | None,
    task_type: str,
    page_all: bool,
    page_limit: int,
) -> tuple[list[Mapping[str, Any]], str | None, bool, int]:
    items: list[Mapping[str, Any]] = []
    page_token: str | None = None
    has_more = False
    pages = 0
    while True:
        payload = service.list_tasks(
            type=task_type,
            page_size=50,
            page_token=page_token,
            completed=completed,
            user_id_type="open_id",
        )
        pages += 1
        batch = payload.get("items")
        if isinstance(batch, list):
            for item in batch:
                if isinstance(item, Mapping):
                    items.append(item)
        has_more = bool(payload.get("has_more"))
        next_page = _optional_string(payload.get("page_token"))
        if not page_all or not has_more or not next_page:
            page_token = next_page
            break
        if page_limit > 0 and pages >= page_limit:
            page_token = next_page
            break
        page_token = next_page
    return items, page_token, has_more, pages


def _cmd_task_create_shortcut(args: argparse.Namespace) -> Mapping[str, Any]:
    service = TaskService(_build_client(args))
    payload = _build_task_create_payload(args)
    result = service.create_task(payload, user_id_type="open_id")
    return _normalize_task_payload(result)


def _cmd_task_comment_shortcut(args: argparse.Namespace) -> Mapping[str, Any]:
    service = TaskService(_build_client(args))
    result = service.create_comment(str(args.task_id), str(args.content))
    return dict(result, task_id=str(args.task_id))


def _cmd_task_delete_shortcut(args: argparse.Namespace) -> Mapping[str, Any]:
    service = TaskService(_build_client(args))
    task_id = str(args.task_id)
    result = service.delete_task(task_id)
    return _normalize_task_payload(result, task_id=task_id, guid=task_id, deleted=True)


def _cmd_task_complete_shortcut(args: argparse.Namespace) -> Mapping[str, Any]:
    service = TaskService(_build_client(args))
    task_id = str(args.task_id)
    current = service.get_task(task_id, user_id_type="open_id")
    task = _task_mapping(current)
    if _task_is_completed(task):
        return _normalize_task_payload(current, changed=False, completed=True)
    result = service.update_task(
        task_id,
        {"completed_at": str(int(_local_now().timestamp() * 1000))},
        update_fields=["completed_at"],
        user_id_type="open_id",
    )
    return _normalize_task_payload(result, changed=True, completed=True)


def _cmd_task_reopen_shortcut(args: argparse.Namespace) -> Mapping[str, Any]:
    service = TaskService(_build_client(args))
    result = service.update_task(
        str(args.task_id),
        {"completed_at": "0"},
        update_fields=["completed_at"],
        user_id_type="open_id",
    )
    return _normalize_task_payload(result, changed=True, completed=False)


def _update_task_members(
    args: argparse.Namespace,
    *,
    role: str,
) -> Mapping[str, Any]:
    task_id = str(args.task_id)
    add_ids = _split_member_ids(getattr(args, "add", None))
    remove_ids = _split_member_ids(getattr(args, "remove", None))
    if not add_ids and not remove_ids:
        raise ValueError("must specify at least one of --add or --remove")

    service = TaskService(_build_client(args))
    result: Mapping[str, Any] | None = None
    if add_ids:
        result = service.add_task_members(
            task_id,
            _task_member_payload(add_ids, role=role),
            client_token=_optional_string(getattr(args, "idempotency_key", None)),
            user_id_type="open_id",
        )
    if remove_ids:
        result = service.remove_task_members(
            task_id,
            _task_member_payload(remove_ids, role=role),
            user_id_type="open_id",
        )
    if result is None:
        raise ValueError("no member updates were submitted")

    task = _task_mapping(result)
    member_ids = _member_ids_by_role(task, role=role)
    return _normalize_task_payload(
        result,
        member_role=role,
        member_ids=member_ids,
        member_count=len(member_ids),
    )


def _cmd_task_assign_shortcut(args: argparse.Namespace) -> Mapping[str, Any]:
    return _update_task_members(args, role="assignee")


def _cmd_task_followers_shortcut(args: argparse.Namespace) -> Mapping[str, Any]:
    return _update_task_members(args, role="follower")


def _cmd_task_reminder_shortcut(args: argparse.Namespace) -> Mapping[str, Any]:
    task_id = str(args.task_id)
    reminder_value = _optional_string(getattr(args, "set", None))
    remove_all = bool(getattr(args, "remove", False))
    if reminder_value and remove_all:
        raise ValueError("cannot use --set together with --remove")
    if not reminder_value and not remove_all:
        raise ValueError("must specify either --set or --remove")

    service = TaskService(_build_client(args))
    current = service.get_task(task_id, user_id_type="open_id")
    task = _task_mapping(current)
    reminder_ids = _task_reminder_ids(task)

    if reminder_ids:
        service.remove_task_reminders(task_id, reminder_ids, user_id_type="open_id")

    relative_fire_minute: int | None = None
    changed = bool(reminder_ids)
    if reminder_value is not None:
        relative_fire_minute = _parse_relative_fire_minutes(reminder_value)
        service.add_task_reminders(
            task_id,
            [{"relative_fire_minute": relative_fire_minute}],
            user_id_type="open_id",
        )
        changed = True

    result = current if not changed else service.get_task(task_id, user_id_type="open_id")
    return _normalize_task_payload(
        result,
        changed=changed,
        reminder_count=len(_task_reminder_ids(_task_mapping(result))),
        relative_fire_minute=relative_fire_minute,
    )


def _cmd_task_get_my_tasks_shortcut(args: argparse.Namespace) -> Mapping[str, Any]:
    service = TaskService(_build_client(args))
    items, page_token, has_more, pages = _fetch_task_pages(
        service,
        completed=True if bool(getattr(args, "complete", False)) else False,
        task_type="my_tasks",
        page_all=bool(getattr(args, "page_all", False)),
        page_limit=int(getattr(args, "page_limit", 20) or 20),
    )

    created_after_ms = None
    if _optional_string(getattr(args, "created_at", None)):
        created_after_ms = _filter_time_ms(str(args.created_at))

    due_start_ms = None
    if _optional_string(getattr(args, "due_start", None)):
        due_start_ms = _filter_time_ms(str(args.due_start))

    due_end_ms = None
    if _optional_string(getattr(args, "due_end", None)):
        due_end_ms = _filter_time_ms(str(args.due_end), upper_bound=True)

    filtered: list[Mapping[str, Any]] = []
    for item in items:
        created_raw = _optional_string(item.get("created_at"))
        if created_after_ms is not None:
            if not created_raw or int(created_raw) < created_after_ms:
                continue

        due_payload = item.get("due")
        due_ts_raw = None
        if isinstance(due_payload, Mapping):
            due_ts_raw = _optional_string(due_payload.get("timestamp"))
        if due_start_ms is not None or due_end_ms is not None:
            if not due_ts_raw:
                continue
            due_ms = int(due_ts_raw)
            if due_start_ms is not None and due_ms < due_start_ms:
                continue
            if due_end_ms is not None and due_ms > due_end_ms:
                continue

        filtered.append(item)

    query = _optional_string(getattr(args, "query", None))
    if query is not None:
        exact = [item for item in filtered if _optional_string(item.get("summary")) == query]
        partial = [item for item in filtered if query in str(item.get("summary") or "")]
        filtered = exact or partial

    normalized = [_normalize_task_item(item) for item in filtered]
    return {
        "items": normalized,
        "count": len(normalized),
        "page_token": page_token,
        "has_more": has_more,
        "pages": pages,
    }


__all__ = [
    "_cmd_task_assign_shortcut",
    "_cmd_task_comment_shortcut",
    "_cmd_task_complete_shortcut",
    "_cmd_task_create_shortcut",
    "_cmd_task_delete_shortcut",
    "_cmd_task_followers_shortcut",
    "_cmd_task_get_my_tasks_shortcut",
    "_cmd_task_reminder_shortcut",
    "_cmd_task_reopen_shortcut",
]
