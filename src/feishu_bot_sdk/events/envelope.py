from typing import Any, Mapping, MutableMapping, Optional

from .types import EventContext, EventEnvelope


def _as_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _as_optional_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def detect_event_schema(payload: Mapping[str, Any]) -> str:
    schema = _as_optional_str(payload.get("schema"))
    if schema == "2.0" and isinstance(payload.get("header"), Mapping):
        return "p2"
    if "uuid" in payload or "ts" in payload:
        return "p1"
    if isinstance(payload.get("event"), Mapping):
        return "p1"
    return "unknown"


def parse_event_envelope(
    payload: Mapping[str, Any],
    *,
    is_callback: bool = False,
) -> EventEnvelope:
    schema = detect_event_schema(payload)

    if schema == "p2":
        return _parse_p2_envelope(payload, is_callback=is_callback)
    if schema == "p1":
        return _parse_p1_envelope(payload, is_callback=is_callback)
    return _parse_unknown_envelope(payload, is_callback=is_callback)


def build_event_context(
    payload: Mapping[str, Any],
    *,
    is_callback: bool = False,
) -> EventContext:
    envelope = parse_event_envelope(payload, is_callback=is_callback)
    event = payload.get("event")
    if event is None:
        event = {}
    return EventContext(envelope=envelope, payload=dict(payload), event=event)


def _parse_p2_envelope(payload: Mapping[str, Any], *, is_callback: bool) -> EventEnvelope:
    header = _as_mapping(payload.get("header"))
    challenge = _as_optional_str(payload.get("challenge"))
    event_type = _as_optional_str(header.get("event_type")) or _as_optional_str(payload.get("type")) or ""
    if not event_type and challenge is not None:
        event_type = "url_verification"

    return EventEnvelope(
        schema="p2",
        event_type=event_type,
        event_id=_as_optional_str(header.get("event_id")),
        token=_as_optional_str(header.get("token")),
        tenant_key=_as_optional_str(header.get("tenant_key")),
        app_id=_as_optional_str(header.get("app_id")),
        create_time=_as_optional_str(header.get("create_time")),
        challenge=challenge,
        is_callback=is_callback,
        raw=_clone_mapping(payload),
    )


def _parse_p1_envelope(payload: Mapping[str, Any], *, is_callback: bool) -> EventEnvelope:
    event = _as_mapping(payload.get("event"))
    challenge = _as_optional_str(payload.get("challenge"))
    event_type = _as_optional_str(event.get("type")) or _as_optional_str(payload.get("type")) or ""
    if not event_type and challenge is not None:
        event_type = "url_verification"

    return EventEnvelope(
        schema="p1",
        event_type=event_type,
        event_id=_as_optional_str(payload.get("uuid")),
        token=_as_optional_str(payload.get("token")),
        tenant_key=_as_optional_str(event.get("tenant_key")) or _as_optional_str(payload.get("tenant_key")),
        app_id=_as_optional_str(event.get("app_id")) or _as_optional_str(payload.get("app_id")),
        create_time=_as_optional_str(payload.get("ts")),
        challenge=challenge,
        is_callback=is_callback,
        raw=_clone_mapping(payload),
    )


def _parse_unknown_envelope(payload: Mapping[str, Any], *, is_callback: bool) -> EventEnvelope:
    challenge = _as_optional_str(payload.get("challenge"))
    event_type = _as_optional_str(payload.get("type")) or ""
    if not event_type and challenge is not None:
        event_type = "url_verification"
    return EventEnvelope(
        schema="unknown",
        event_type=event_type,
        challenge=challenge,
        is_callback=is_callback,
        raw=_clone_mapping(payload),
    )


def _clone_mapping(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    cloned: MutableMapping[str, Any] = {}
    for key, value in payload.items():
        cloned[str(key)] = value
    return cloned
