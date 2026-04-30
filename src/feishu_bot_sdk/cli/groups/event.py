from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import click

from ...events import build_event_context
from ..context import build_cli_context, with_runtime_options
from ..runtime.registry import metadata_root
from ..runtime.output import _build_event_view


@dataclass(frozen=True)
class EventDefinition:
    key: str
    event_type: str
    description: str
    auth_types: tuple[str, ...] = ("bot", "user")
    scopes: tuple[str, ...] = ()
    params: tuple[Mapping[str, Any], ...] = ()
    jq_root_path: str = ".event"


_EVENT_DEFINITIONS: tuple[EventDefinition, ...] = (
    EventDefinition(
        key="im.message.receive_v1",
        event_type="im.message.receive_v1",
        description="Message received event",
        scopes=("im:message",),
    ),
    EventDefinition(
        key="im.message.message_read_v1",
        event_type="im.message.message_read_v1",
        description="Message read event",
        scopes=("im:message",),
    ),
    EventDefinition(
        key="im.message.recalled_v1",
        event_type="im.message.recalled_v1",
        description="Message recalled event",
        scopes=("im:message",),
    ),
    EventDefinition(
        key="im.message.reaction.created_v1",
        event_type="im.message.reaction.created_v1",
        description="Message reaction created event",
        scopes=("im:message",),
    ),
    EventDefinition(
        key="im.message.reaction.deleted_v1",
        event_type="im.message.reaction.deleted_v1",
        description="Message reaction deleted event",
        scopes=("im:message",),
    ),
    EventDefinition(
        key="application.bot.menu_v6",
        event_type="application.bot.menu_v6",
        description="Bot menu clicked event",
        auth_types=("bot",),
    ),
    EventDefinition(
        key="card.action.trigger",
        event_type="card.action.trigger",
        description="Interactive card action event",
    ),
    EventDefinition(
        key="url.preview.get",
        event_type="url.preview.get",
        description="URL preview request event",
    ),
    EventDefinition(
        key="drive.file.bitable_record_changed_v1",
        event_type="drive.file.bitable_record_changed_v1",
        description="Bitable record changed event",
        scopes=("drive:drive",),
    ),
    EventDefinition(
        key="drive.file.bitable_field_changed_v1",
        event_type="drive.file.bitable_field_changed_v1",
        description="Bitable field changed event",
        scopes=("drive:drive",),
    ),
)


@click.group("event", help="Consume and inspect local event definitions")
def event_group() -> None:
    pass


@event_group.command("list")
@with_runtime_options(include_identity=False)
def event_list(**kwargs: Any) -> None:
    cli_ctx, _params = build_cli_context(kwargs)
    cli_ctx.emit(
        [_definition_payload(definition, include_schema=False) for definition in _EVENT_DEFINITIONS],
        cli_args=cli_ctx.build_args(group="event", command="list"),
    )


@event_group.command("schema")
@click.argument("key")
@with_runtime_options(include_identity=False)
def event_schema(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    definition = _lookup_definition(str(params.get("key") or ""))
    if definition is None:
        raise ValueError(f"unknown event key {params.get('key')!r}")
    cli_ctx.emit(
        _definition_payload(definition, include_schema=True),
        cli_args=cli_ctx.build_args(group="event", command="schema"),
    )


@event_group.command("consume")
@click.argument("key")
@click.option("--stdin", "from_stdin", is_flag=True, help="Consume a single event payload from stdin")
@click.option("--include-payload", is_flag=True, help="Include the raw payload in output")
@with_runtime_options(include_identity=False)
def event_consume(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    key = str(params.get("key") or "")
    definition = _lookup_definition(key)
    if definition is None:
        raise ValueError(f"unknown event key {key!r}")
    if not bool(params.get("from_stdin")):
        state = {
            "running": True,
            "event_key": key,
            "pid": os.getpid(),
            "started_at": time.time(),
        }
        _write_state(state)
        cli_ctx.emit(
            {
                "running": True,
                "event_key": key,
                "state_path": str(_event_state_path()),
                "mode": "local-placeholder",
                "message": "live event streaming is not started by this foundation command; use --stdin for single-payload consumption",
            },
            cli_args=cli_ctx.build_args(group="event", command="consume"),
        )
        return

    payload = _read_stdin_json()
    context = build_event_context(payload)
    if context.envelope.event_type and context.envelope.event_type != definition.event_type:
        raise ValueError(
            f"stdin event_type {context.envelope.event_type!r} does not match requested key {key!r}"
        )
    cli_ctx.emit(
        _build_event_view(context, include_payload=bool(params.get("include_payload"))),
        cli_args=cli_ctx.build_args(group="event", command="consume"),
    )


@event_group.command("status")
@with_runtime_options(include_identity=False)
def event_status(**kwargs: Any) -> None:
    cli_ctx, _params = build_cli_context(kwargs)
    state = _read_state()
    running = bool(state.get("running"))
    cli_ctx.emit(
        {
            "running": running,
            "pid": state.get("pid"),
            "event_key": state.get("event_key"),
            "started_at": state.get("started_at"),
            "state_path": str(_event_state_path()),
        },
        cli_args=cli_ctx.build_args(group="event", command="status"),
    )


@event_group.command("stop")
@with_runtime_options(include_identity=False)
def event_stop(**kwargs: Any) -> None:
    cli_ctx, _params = build_cli_context(kwargs)
    state = _read_state()
    was_running = bool(state.get("running"))
    state["running"] = False
    state["stopped_at"] = time.time()
    _write_state(state)
    cli_ctx.emit(
        {
            "stopped": was_running,
            "pid": state.get("pid"),
            "event_key": state.get("event_key"),
            "state_path": str(_event_state_path()),
        },
        cli_args=cli_ctx.build_args(group="event", command="stop"),
    )


def _definition_payload(definition: EventDefinition, *, include_schema: bool) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "key": definition.key,
        "event_type": definition.event_type,
        "description": definition.description,
        "auth_types": list(definition.auth_types),
        "scopes": list(definition.scopes),
        "params": [dict(item) for item in definition.params],
    }
    if include_schema:
        payload["resolved_output_schema"] = _event_schema_payload(definition)
        payload["jq_root_path"] = definition.jq_root_path
        payload["schema_snapshot"] = load_event_schema_snapshot()
    return payload


def _event_schema_payload(definition: EventDefinition) -> dict[str, Any]:
    snapshot = load_event_schema_snapshot()
    envelope = snapshot.get("v2_envelope")
    if isinstance(envelope, Mapping):
        schema = json.loads(json.dumps(envelope))
        properties = schema.setdefault("properties", {})
        if isinstance(properties, dict):
            properties["event"] = {"type": "object"}
            header = properties.get("header")
            if isinstance(header, dict):
                header_properties = header.setdefault("properties", {})
                if isinstance(header_properties, dict):
                    event_type = header_properties.setdefault("event_type", {"type": "string"})
                    if isinstance(event_type, dict):
                        event_type["const"] = definition.event_type
        schema.setdefault("required", ["header", "event"])
        return schema
    return {
        "type": "object",
        "properties": {
            "schema": {"type": "string"},
            "header": {
                "type": "object",
                "properties": {
                    "event_id": {"type": "string"},
                    "event_type": {"const": definition.event_type},
                    "tenant_key": {"type": "string"},
                    "app_id": {"type": "string"},
                    "create_time": {"type": "string"},
                },
            },
            "event": {"type": "object"},
        },
        "required": ["header", "event"],
    }


@lru_cache(maxsize=1)
def load_event_schema_snapshot() -> dict[str, Any]:
    path = metadata_root() / "events" / "schemas.json"
    if not path.exists():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return dict(parsed) if isinstance(parsed, Mapping) else {}


def _lookup_definition(key: str) -> EventDefinition | None:
    for definition in _EVENT_DEFINITIONS:
        if definition.key == key or definition.event_type == key:
            return definition
    return None


def _read_stdin_json() -> Mapping[str, Any]:
    import sys

    text = sys.stdin.read()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"stdin did not contain valid JSON: {exc}") from exc
    if not isinstance(parsed, Mapping):
        raise ValueError("stdin JSON payload must be an object")
    return parsed


def _event_state_path() -> Path:
    override = os.getenv("FEISHU_EVENT_STATE_PATH")
    if override:
        return Path(override)
    config_home = os.getenv("XDG_STATE_HOME")
    if config_home:
        return Path(config_home) / "feishu-bot-sdk" / "event-state.json"
    return Path.home() / ".local" / "state" / "feishu-bot-sdk" / "event-state.json"


def _read_state() -> dict[str, Any]:
    path = _event_state_path()
    if not path.exists():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return dict(parsed) if isinstance(parsed, Mapping) else {}


def _write_state(state: Mapping[str, Any]) -> None:
    path = _event_state_path()
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(state), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


__all__ = ["event_group"]
