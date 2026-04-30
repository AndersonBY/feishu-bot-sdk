from __future__ import annotations

import argparse
from datetime import datetime, time, timezone
from typing import Any, Mapping
from urllib.parse import quote, urlparse

from ..runtime import _build_client


def _data(response: Mapping[str, Any]) -> dict[str, Any]:
    payload = response.get("data")
    if isinstance(payload, Mapping):
        return {str(key): value for key, value in payload.items()}
    return {}


def _split_csv(value: Any) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _to_rfc3339(value: str, *, end: bool = False) -> str:
    text = value.strip()
    if not text:
        return ""
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        parsed_date = datetime.strptime(text, "%Y-%m-%d").date()
        parsed_dt = datetime.combine(parsed_date, time.max if end else time.min, tzinfo=timezone.utc)
        return parsed_dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    normalized = text.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.isoformat().replace("+00:00", "Z")


def _build_time_filter(start: str, end: str) -> dict[str, str]:
    if not start and not end:
        return {}
    payload: dict[str, str] = {}
    if start:
        payload["start_time"] = _to_rfc3339(start)
    if end:
        payload["end_time"] = _to_rfc3339(end, end=True)
    if "start_time" in payload and "end_time" in payload:
        start_dt = datetime.fromisoformat(payload["start_time"].replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(payload["end_time"].replace("Z", "+00:00"))
        if start_dt > end_dt:
            raise ValueError(f"--start ({start}) is after --end ({end})")
    return payload


def _build_vc_search_body(args: argparse.Namespace) -> dict[str, Any]:
    body: dict[str, Any] = {}
    query = str(getattr(args, "query", "") or "").strip()
    if query:
        if len(query) > 50:
            raise ValueError("--query: length must be between 1 and 50 characters")
        body["query"] = query

    meeting_filter: dict[str, Any] = {}
    time_filter = _build_time_filter(
        str(getattr(args, "start", "") or "").strip(),
        str(getattr(args, "end", "") or "").strip(),
    )
    if time_filter:
        meeting_filter["start_time"] = time_filter
    participant_ids = _unique(_split_csv(getattr(args, "participant_ids", None)))
    organizer_ids = _split_csv(getattr(args, "organizer_ids", None))
    room_ids = _split_csv(getattr(args, "room_ids", None))
    if participant_ids:
        meeting_filter["participant_ids"] = participant_ids
    if organizer_ids:
        meeting_filter["organizer_ids"] = organizer_ids
    if room_ids:
        meeting_filter["open_room_ids"] = room_ids
    if meeting_filter:
        body["meeting_filter"] = meeting_filter
    return body


def _validate_vc_search(args: argparse.Namespace) -> None:
    page_size = int(getattr(args, "page_size", 15) or 15)
    if page_size < 1 or page_size > 30:
        raise ValueError("--page-size: must be between 1 and 30")
    has_filter = any(
        str(getattr(args, name, "") or "").strip()
        for name in ("query", "start", "end", "organizer_ids", "participant_ids", "room_ids")
    )
    if not has_filter:
        raise ValueError("specify at least one of --query, --start, --end, --organizer-ids, --participant-ids, or --room-ids")


def _extract_string_slice(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _artifact_type(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def _fetch_note_detail(client: Any, note_id: str) -> dict[str, Any]:
    data = _data(client.request_json("GET", f"/vc/v1/notes/{quote(note_id, safe='')}"))
    note = data.get("note")
    if not isinstance(note, Mapping):
        return {"error": "note detail is empty"}
    note_doc_token = ""
    verbatim_doc_token = ""
    artifacts = note.get("artifacts")
    if isinstance(artifacts, list):
        for item in artifacts:
            if not isinstance(item, Mapping):
                continue
            doc_token = str(item.get("doc_token") or "")
            if _artifact_type(item.get("artifact_type")) == 1:
                note_doc_token = doc_token
            elif _artifact_type(item.get("artifact_type")) == 2:
                verbatim_doc_token = doc_token
    shared_doc_tokens: list[str] = []
    references = note.get("references")
    if isinstance(references, list):
        for item in references:
            if isinstance(item, Mapping):
                token = str(item.get("doc_token") or "")
                if token:
                    shared_doc_tokens.append(token)
    result: dict[str, Any] = {
        "creator_id": note.get("creator_id"),
        "create_time": note.get("create_time"),
        "note_doc_token": note_doc_token,
        "verbatim_doc_token": verbatim_doc_token,
    }
    if shared_doc_tokens:
        result["shared_doc_tokens"] = shared_doc_tokens
    return result


def _fetch_note_by_meeting_id(client: Any, meeting_id: str) -> dict[str, Any]:
    data = _data(
        client.request_json(
            "GET",
            f"/vc/v1/meetings/{quote(meeting_id, safe='')}",
            params={"with_participants": "false", "query_mode": "0"},
        )
    )
    meeting = data.get("meeting")
    if not isinstance(meeting, Mapping):
        return {"meeting_id": meeting_id, "error": "meeting not found"}
    note_id = str(meeting.get("note_id") or "")
    if not note_id:
        return {"meeting_id": meeting_id, "error": "no notes available for this meeting"}
    result = _fetch_note_detail(client, note_id)
    result["meeting_id"] = meeting_id
    return result


def _fetch_note_by_minute_token(client: Any, minute_token: str) -> dict[str, Any]:
    data = _data(client.request_json("GET", f"/minutes/v1/minutes/{quote(minute_token, safe='')}"))
    minute = data.get("minute")
    if not isinstance(minute, Mapping):
        return {"minute_token": minute_token, "error": "minutes not found"}
    result: dict[str, Any] = {"minute_token": minute_token}
    title = str(minute.get("title") or "")
    if title:
        result["title"] = title
    note_id = str(minute.get("note_id") or "")
    if note_id:
        detail = _fetch_note_detail(client, note_id)
        if "error" not in detail:
            result.update(detail)
        else:
            result["note_error"] = detail["error"]
    artifacts_data = _data(client.request_json("GET", f"/minutes/v1/minutes/{quote(minute_token, safe='')}/artifacts"))
    artifacts: dict[str, Any] = {}
    for source_key, target_key in (("summary", "summary"), ("minute_todos", "todos"), ("minute_chapters", "chapters")):
        value = artifacts_data.get(source_key)
        if value:
            artifacts[target_key] = value
    if artifacts:
        result["artifacts"] = artifacts
    return result


def _get_primary_calendar_id(client: Any) -> str:
    data = _data(client.request_json("POST", "/calendar/v4/calendars/primary"))
    calendars = data.get("calendars")
    if isinstance(calendars, list) and calendars:
        first = calendars[0]
        if isinstance(first, Mapping):
            calendar = first.get("calendar")
            if isinstance(calendar, Mapping):
                calendar_id = str(calendar.get("calendar_id") or "")
                if calendar_id:
                    return calendar_id
    raise ValueError("primary calendar not found")


def _resolve_meeting_ids_from_calendar_event(client: Any, calendar_id: str, instance_id: str, *, need_notes: bool) -> tuple[list[str], list[str]]:
    body: dict[str, Any] = {
        "instance_ids": [instance_id],
        "need_meeting_instance_ids": True,
    }
    if need_notes:
        body["need_meeting_notes"] = True
    data = _data(
        client.request_json(
            "POST",
            f"/calendar/v4/calendars/{quote(calendar_id, safe='')}/events/mget_instance_relation_info",
            payload=body,
        )
    )
    infos = data.get("instance_relation_infos")
    if not isinstance(infos, list) or not infos:
        raise ValueError("no event relation info found")
    info = infos[0]
    if not isinstance(info, Mapping):
        raise ValueError("no event relation info found")
    meeting_ids = [str(item) for item in info.get("meeting_instance_ids", []) if item]
    if not meeting_ids:
        raise ValueError("no associated video meeting for this event")
    return meeting_ids, _extract_string_slice(info.get("meeting_notes"))


def _fetch_note_by_calendar_event_id(client: Any, calendar_id: str, instance_id: str) -> dict[str, Any]:
    try:
        meeting_ids, meeting_notes = _resolve_meeting_ids_from_calendar_event(client, calendar_id, instance_id, need_notes=True)
    except Exception as exc:
        return {"calendar_event_id": instance_id, "error": str(exc)}
    result: dict[str, Any] = {"calendar_event_id": instance_id}
    if meeting_notes:
        result["meeting_notes"] = meeting_notes
    for meeting_id in meeting_ids:
        note = _fetch_note_by_meeting_id(client, meeting_id)
        if "error" not in note:
            result.update(note)
            return result
    if meeting_notes:
        return result
    result["error"] = "no notes found in any associated meeting"
    return result


def _extract_minute_token(recording_url: str) -> str:
    parsed = urlparse(recording_url)
    parts = [part for part in parsed.path.rstrip("/").split("/") if part]
    for index, part in enumerate(parts):
        if part == "minutes" and index + 1 < len(parts):
            return parts[index + 1]
    return ""


def _fetch_recording_by_meeting_id(client: Any, meeting_id: str) -> dict[str, Any]:
    data = _data(client.request_json("GET", f"/vc/v1/meetings/{quote(meeting_id, safe='')}/recording"))
    recording = data.get("recording")
    if not isinstance(recording, Mapping):
        return {"meeting_id": meeting_id, "error": "no recording available for this meeting"}
    url = str(recording.get("url") or "")
    result: dict[str, Any] = {"meeting_id": meeting_id}
    if url:
        result["recording_url"] = url
    duration = str(recording.get("duration") or "")
    if duration:
        result["duration"] = duration
    minute_token = _extract_minute_token(url)
    if minute_token:
        result["minute_token"] = minute_token
    return result


def _fetch_recording_by_calendar_event_id(client: Any, calendar_id: str, instance_id: str) -> dict[str, Any]:
    try:
        meeting_ids, _ = _resolve_meeting_ids_from_calendar_event(client, calendar_id, instance_id, need_notes=False)
    except Exception as exc:
        return {"calendar_event_id": instance_id, "error": str(exc)}
    for meeting_id in meeting_ids:
        recording = _fetch_recording_by_meeting_id(client, meeting_id)
        if "error" not in recording:
            recording["calendar_event_id"] = instance_id
            return recording
    return {"calendar_event_id": instance_id, "error": "no recording found in any associated meeting"}


def _validate_exactly_one(args: argparse.Namespace, *names: str) -> None:
    present = [name for name in names if str(getattr(args, name, "") or "").strip()]
    if len(present) != 1:
        flags = ", ".join(f"--{name.replace('_', '-')}" for name in names)
        raise ValueError(f"exactly one of {flags} is required")
    values = _split_csv(getattr(args, present[0], None))
    if len(values) > 50:
        raise ValueError(f"--{present[0].replace('_', '-')}: too many IDs ({len(values)}), maximum is 50")


def _cmd_vc_search(args: argparse.Namespace) -> Mapping[str, Any]:
    _validate_vc_search(args)
    client = _build_client(args)
    params: dict[str, Any] = {"page_size": int(getattr(args, "page_size", 15) or 15)}
    page_token = str(getattr(args, "page_token", "") or "").strip()
    if page_token:
        params["page_token"] = page_token
    data = _data(
        client.request_json(
            "POST",
            "/vc/v1/meetings/search",
            params=params,
            payload=_build_vc_search_body(args),
        )
    )
    items = data.get("items") if isinstance(data.get("items"), list) else []
    return {
        "items": items,
        "total": data.get("total"),
        "has_more": data.get("has_more"),
        "page_token": data.get("page_token"),
    }


def _cmd_vc_notes(args: argparse.Namespace) -> Mapping[str, Any]:
    _validate_exactly_one(args, "meeting_ids", "minute_tokens", "calendar_event_ids")
    client = _build_client(args)
    results: list[dict[str, Any]] = []
    if str(getattr(args, "meeting_ids", "") or "").strip():
        for meeting_id in _split_csv(getattr(args, "meeting_ids", None)):
            results.append(_fetch_note_by_meeting_id(client, meeting_id))
    elif str(getattr(args, "minute_tokens", "") or "").strip():
        for token in _split_csv(getattr(args, "minute_tokens", None)):
            results.append(_fetch_note_by_minute_token(client, token))
    else:
        calendar_id = _get_primary_calendar_id(client)
        for instance_id in _split_csv(getattr(args, "calendar_event_ids", None)):
            results.append(_fetch_note_by_calendar_event_id(client, calendar_id, instance_id))
    return {
        "notes": results,
        "count": len(results),
        "success_count": sum(1 for item in results if "error" not in item),
        "failure_count": sum(1 for item in results if "error" in item),
    }


def _cmd_vc_recording(args: argparse.Namespace) -> Mapping[str, Any]:
    _validate_exactly_one(args, "meeting_ids", "calendar_event_ids")
    client = _build_client(args)
    results: list[dict[str, Any]] = []
    if str(getattr(args, "meeting_ids", "") or "").strip():
        for meeting_id in _split_csv(getattr(args, "meeting_ids", None)):
            results.append(_fetch_recording_by_meeting_id(client, meeting_id))
    else:
        calendar_id = _get_primary_calendar_id(client)
        for instance_id in _split_csv(getattr(args, "calendar_event_ids", None)):
            results.append(_fetch_recording_by_calendar_event_id(client, calendar_id, instance_id))
    return {
        "recordings": results,
        "count": len(results),
        "success_count": sum(1 for item in results if "error" not in item),
        "failure_count": sum(1 for item in results if "error" in item),
    }


__all__ = ["_cmd_vc_notes", "_cmd_vc_recording", "_cmd_vc_search"]
