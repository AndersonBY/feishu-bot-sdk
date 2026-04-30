from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

from ...events import build_event_context
from ..runtime.output import _build_event_view


def _read_stdin_json() -> Mapping[str, Any]:
    try:
        text = sys.stdin.read()
    except OSError as exc:
        raise ValueError("stdin event payload is unavailable; pass input on stdin or use Click invocation with input") from exc
    if not text.strip():
        raise ValueError("stdin did not contain an event JSON payload")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"stdin did not contain valid JSON: {exc}") from exc
    if not isinstance(parsed, Mapping):
        raise ValueError("stdin JSON payload must be an object")
    return parsed


def _event_id(payload: Mapping[str, Any], view: Mapping[str, Any]) -> str:
    value = view.get("event_id")
    if isinstance(value, str) and value:
        return value
    header = payload.get("header")
    if isinstance(header, Mapping):
        value = header.get("event_id")
        if isinstance(value, str) and value:
            return value
    return "event"


def _write_event(output_dir: str, payload: Mapping[str, Any], view: Mapping[str, Any]) -> str:
    target_dir = Path(output_dir).expanduser()
    target_dir.mkdir(parents=True, exist_ok=True)
    event_id = _event_id(payload, view)
    target = target_dir / f"{event_id}.json"
    persisted = dict(payload)
    persisted.setdefault("event_id", event_id)
    target.write_text(json.dumps(persisted, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(target)


def _cmd_event_subscribe(args: argparse.Namespace) -> Mapping[str, Any]:
    if not bool(getattr(args, "stdin", False)):
        return {
            "mode": "websocket",
            "event_types": str(getattr(args, "event_types", "") or ""),
            "filter": str(getattr(args, "filter", "") or ""),
            "output_dir": str(getattr(args, "output_dir", "") or ""),
            "route": list(getattr(args, "route", ()) or ()),
            "message": "live WebSocket subscription is not implemented in this Python parity shortcut; use --stdin for single-event consumption",
        }
    payload = _read_stdin_json()
    context = build_event_context(payload)
    view = dict(_build_event_view(context, include_payload=not bool(getattr(args, "compact", False))))
    output_dir = str(getattr(args, "output_dir", "") or "").strip()
    if output_dir:
        view["output_path"] = _write_event(output_dir, payload, view)
    return view


__all__ = ["_cmd_event_subscribe"]
