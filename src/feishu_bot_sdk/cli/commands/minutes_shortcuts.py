from __future__ import annotations

import argparse
from datetime import datetime, time, timezone
from typing import Any, Mapping

from ..runtime import _build_client


def _data(response: Mapping[str, Any]) -> dict[str, Any]:
    payload = response.get("data")
    if isinstance(payload, Mapping):
        return {str(key): value for key, value in payload.items()}
    return {}


def _split_csv(value: Any) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


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


def _time_filter(start: str, end: str) -> dict[str, Any]:
    if not start and not end:
        return {}
    payload: dict[str, Any] = {}
    if start:
        payload["start_time"] = _to_rfc3339(start)
    if end:
        payload["end_time"] = _to_rfc3339(end, end=True)
    if "start_time" in payload and "end_time" in payload:
        start_dt = datetime.fromisoformat(str(payload["start_time"]).replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(str(payload["end_time"]).replace("Z", "+00:00"))
        if start_dt > end_dt:
            raise ValueError(f"--start ({start}) is after --end ({end})")
    return payload


def _build_minutes_search_body(args: argparse.Namespace) -> dict[str, Any]:
    body: dict[str, Any] = {}
    query = str(getattr(args, "query", "") or "").strip()
    if query:
        if len(query) > 50:
            raise ValueError("--query: length must be between 1 and 50 characters")
        body["query"] = query

    filter_payload: dict[str, Any] = {}
    owner_ids = _split_csv(getattr(args, "owner_ids", None))
    participant_ids = _split_csv(getattr(args, "participant_ids", None))
    if owner_ids:
        filter_payload["owner_ids"] = owner_ids
    if participant_ids:
        filter_payload["participant_ids"] = participant_ids
    time_payload = _time_filter(
        str(getattr(args, "start", "") or "").strip(),
        str(getattr(args, "end", "") or "").strip(),
    )
    if time_payload:
        filter_payload["create_time"] = time_payload
    if filter_payload:
        body["filter"] = filter_payload
    return body


def _validate_minutes_search(args: argparse.Namespace) -> None:
    page_size = int(getattr(args, "page_size", 15) or 15)
    if page_size < 1 or page_size > 30:
        raise ValueError("--page-size: must be between 1 and 30")
    has_filter = any(
        str(getattr(args, name, "") or "").strip()
        for name in ("query", "owner_ids", "participant_ids", "start", "end")
    )
    if not has_filter:
        raise ValueError("specify at least one of --query, --owner-ids, --participant-ids, --start, or --end")


def _cmd_minutes_search(args: argparse.Namespace) -> Mapping[str, Any]:
    _validate_minutes_search(args)
    client = _build_client(args)
    params: dict[str, Any] = {"page_size": int(getattr(args, "page_size", 15) or 15)}
    page_token = str(getattr(args, "page_token", "") or "").strip()
    if page_token:
        params["page_token"] = page_token
    data = _data(
        client.request_json(
            "POST",
            "/minutes/v1/minutes/search",
            params=params,
            payload=_build_minutes_search_body(args),
        )
    )
    items = data.get("items") if isinstance(data.get("items"), list) else []
    return {
        "items": items,
        "total": data.get("total"),
        "has_more": data.get("has_more"),
        "page_token": data.get("page_token"),
    }


__all__ = ["_cmd_minutes_search"]
