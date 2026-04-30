from __future__ import annotations

import argparse
from datetime import datetime, timezone
import re
from typing import Any, Mapping
from urllib.parse import quote

from ..runtime import _build_client


def _data(response: Mapping[str, Any]) -> dict[str, Any]:
    payload = response.get("data")
    if isinstance(payload, Mapping):
        return {str(key): value for key, value in payload.items()}
    return {}


def _split_csv(value: Any) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _calendar_id(args: argparse.Namespace) -> str:
    return str(getattr(args, "calendar_id", "") or "").strip() or "primary"


def _to_timestamp(value: str) -> str:
    text = value.strip()
    if not text:
        raise ValueError("time value cannot be empty")
    if re.fullmatch(r"[1-9]\d*", text):
        return text
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        parsed_date = datetime.strptime(text, "%Y-%m-%d").date()
        parsed_dt = datetime.combine(parsed_date, datetime.min.time(), tzinfo=timezone.utc)
        return str(int(parsed_dt.timestamp()))
    normalized = text.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return str(int(parsed.timestamp()))


def _event_time(value: str) -> dict[str, str]:
    return {"timestamp": _to_timestamp(value)}


def _attendee_payload(attendee_ids: Any) -> list[dict[str, str]]:
    attendees: list[dict[str, str]] = []
    seen: set[str] = set()
    for attendee_id in _split_csv(attendee_ids):
        if attendee_id in seen:
            continue
        seen.add(attendee_id)
        if attendee_id.startswith("ou_"):
            attendees.append({"type": "user", "user_id": attendee_id})
        elif attendee_id.startswith("oc_"):
            attendees.append({"type": "chat", "chat_id": attendee_id})
        elif attendee_id.startswith("omm_"):
            attendees.append({"type": "resource", "room_id": attendee_id})
        else:
            raise ValueError(
                f"invalid attendee id format {attendee_id!r}: should start with 'ou_', 'oc_', or 'omm_'"
            )
    return attendees


def _attendee_buckets(attendee_ids: Any) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = {
        "attendee_user_ids": [],
        "attendee_chat_ids": [],
        "attendee_room_ids": [],
    }
    for attendee_id in _split_csv(attendee_ids):
        if attendee_id.startswith("ou_"):
            buckets["attendee_user_ids"].append(attendee_id)
        elif attendee_id.startswith("oc_"):
            buckets["attendee_chat_ids"].append(attendee_id)
        elif attendee_id.startswith("omm_"):
            buckets["attendee_room_ids"].append(attendee_id)
        else:
            raise ValueError(
                f"invalid attendee id format {attendee_id!r}: should start with 'ou_', 'oc_', or 'omm_'"
            )
    return {key: value for key, value in buckets.items() if value}


def _build_event_body(args: argparse.Namespace) -> dict[str, Any]:
    start = str(getattr(args, "start", "") or "").strip()
    end = str(getattr(args, "end", "") or "").strip()
    if not start:
        raise ValueError("specify --start")
    if not end:
        raise ValueError("specify --end")
    body: dict[str, Any] = {
        "summary": str(getattr(args, "summary", "") or "").strip(),
        "start_time": _event_time(start),
        "end_time": _event_time(end),
        "attendee_ability": "can_modify_event",
        "free_busy_status": "busy",
        "vchat": {"vc_type": "vc"},
        "reminders": [{"minutes": 5}],
    }
    description = str(getattr(args, "description", "") or "").strip()
    if description:
        body["description"] = description
    rrule = str(getattr(args, "rrule", "") or "").strip()
    if rrule:
        body["recurrence"] = rrule
    return body


def _build_update_body(args: argparse.Namespace) -> dict[str, Any]:
    body: dict[str, Any] = {}
    for arg_name in ("summary", "description"):
        value = getattr(args, arg_name, None)
        if value is not None:
            body[arg_name] = str(value)
    rrule = getattr(args, "rrule", None)
    if rrule is not None:
        body["recurrence"] = str(rrule)
    start = str(getattr(args, "start", "") or "").strip()
    end = str(getattr(args, "end", "") or "").strip()
    if bool(start) != bool(end):
        raise ValueError("--start and --end must be specified together when updating event time")
    if start:
        body["start_time"] = _event_time(start)
        body["end_time"] = _event_time(end)
    if body:
        body["need_notification"] = bool(getattr(args, "notify", True))
    return body


def _event_id_from_data(data: Mapping[str, Any]) -> str:
    event = data.get("event")
    if isinstance(event, Mapping):
        return str(event.get("event_id") or "")
    return str(data.get("event_id") or "")


def _cmd_calendar_create(args: argparse.Namespace) -> Mapping[str, Any]:
    client = _build_client(args)
    calendar_id = _calendar_id(args)
    data = _data(
        client.request_json(
            "POST",
            f"/calendar/v4/calendars/{quote(calendar_id, safe='')}/events",
            payload=_build_event_body(args),
        )
    )
    event_id = _event_id_from_data(data)
    attendee_ids = _split_csv(getattr(args, "attendee_ids", None))
    if attendee_ids:
        if not event_id:
            raise ValueError("calendar event create response did not include event_id")
        client.request_json(
            "POST",
            f"/calendar/v4/calendars/{quote(calendar_id, safe='')}/events/{quote(event_id, safe='')}/attendees",
            params={"user_id_type": "open_id"},
            payload={"attendees": _attendee_payload(",".join(attendee_ids)), "need_notification": True},
        )
    event = data.get("event")
    result = dict(event) if isinstance(event, Mapping) else dict(data)
    if event_id:
        result["event_id"] = event_id
    result["calendar_id"] = calendar_id
    return result


def _cmd_calendar_update(args: argparse.Namespace) -> Mapping[str, Any]:
    client = _build_client(args)
    calendar_id = _calendar_id(args)
    event_id = str(getattr(args, "event_id", "") or "").strip()
    if not event_id:
        raise ValueError("specify --event-id")
    path = f"/calendar/v4/calendars/{quote(calendar_id, safe='')}/events/{quote(event_id, safe='')}"
    body = _build_update_body(args)
    result: dict[str, Any] = {"calendar_id": calendar_id, "event_id": event_id}
    if body:
        result.update(_data(client.request_json("PATCH", path, payload=body)))
    remove_attendees = _attendee_payload(getattr(args, "remove_attendee_ids", None))
    if remove_attendees:
        client.request_json(
            "POST",
            f"{path}/attendees/batch_delete",
            params={"user_id_type": "open_id"},
            payload={
                "delete_ids": remove_attendees,
                "need_notification": bool(getattr(args, "notify", True)),
            },
        )
    add_attendees = _attendee_payload(getattr(args, "add_attendee_ids", None))
    if add_attendees:
        client.request_json(
            "POST",
            f"{path}/attendees",
            params={"user_id_type": "open_id"},
            payload={
                "attendees": add_attendees,
                "need_notification": bool(getattr(args, "notify", True)),
            },
        )
    return result


def _cmd_calendar_agenda(args: argparse.Namespace) -> Mapping[str, Any]:
    client = _build_client(args)
    params: dict[str, Any] = {
        "start_time": _to_timestamp(str(getattr(args, "start", "") or "")),
        "end_time": _to_timestamp(str(getattr(args, "end", "") or "")),
    }
    page_size = getattr(args, "page_size", None)
    if page_size:
        params["page_size"] = int(page_size)
    return _data(
        client.request_json(
            "GET",
            f"/calendar/v4/calendars/{quote(_calendar_id(args), safe='')}/events/instance_view",
            params=params,
        )
    )


def _cmd_calendar_freebusy(args: argparse.Namespace) -> Mapping[str, Any]:
    client = _build_client(args)
    body: dict[str, Any] = {
        "start_time": str(getattr(args, "start", "") or "").strip(),
        "end_time": str(getattr(args, "end", "") or "").strip(),
    }
    user_id = str(getattr(args, "user_id", "") or "").strip()
    if user_id:
        body["user_id"] = user_id
    user_ids = _split_csv(getattr(args, "user_ids", None))
    if user_ids:
        body["user_ids"] = user_ids
    return _data(client.request_json("POST", "/calendar/v4/freebusy/list", payload=body))


def _cmd_calendar_suggestion(args: argparse.Namespace) -> Mapping[str, Any]:
    client = _build_client(args)
    body: dict[str, Any] = {
        "duration_minutes": int(getattr(args, "duration_minutes", 30) or 30),
    }
    body.update(_attendee_buckets(getattr(args, "attendee_ids", None)))
    start = str(getattr(args, "start", "") or "").strip()
    end = str(getattr(args, "end", "") or "").strip()
    if start:
        body["start_time"] = start
    if end:
        body["end_time"] = end
    return _data(client.request_json("POST", "/calendar/v4/freebusy/suggestion", payload=body))


def _cmd_calendar_room_find(args: argparse.Namespace) -> Mapping[str, Any]:
    client = _build_client(args)
    body: dict[str, Any] = {}
    slot = str(getattr(args, "slot", "") or "").strip()
    if slot:
        parts = slot.split("~", 1)
        if len(parts) != 2:
            raise ValueError("--slot must use START~END format")
        body["start_time"] = parts[0].strip()
        body["end_time"] = parts[1].strip()
    min_capacity = getattr(args, "min_capacity", None)
    if min_capacity is not None:
        body["min_capacity"] = int(min_capacity)
    building_id = str(getattr(args, "building_id", "") or "").strip()
    if building_id:
        body["building_id"] = building_id
    return _data(client.request_json("POST", "/calendar/v4/freebusy/meeting_room/search", payload=body))


__all__ = [
    "_cmd_calendar_agenda",
    "_cmd_calendar_create",
    "_cmd_calendar_freebusy",
    "_cmd_calendar_room_find",
    "_cmd_calendar_suggestion",
    "_cmd_calendar_update",
]
