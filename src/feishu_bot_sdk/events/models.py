import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from .types import EventContext


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


def _as_optional_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return int(stripped)
        except ValueError:
            return None
    return None


def _as_mapping_list(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    items: list[Mapping[str, Any]] = []
    for item in value:
        if isinstance(item, Mapping):
            items.append(dict(item))
    return items


@dataclass(frozen=True)
class P2ImMessageReceiveV1:
    event_id: Optional[str]
    create_time: Optional[str]
    tenant_key: Optional[str]
    app_id: Optional[str]
    message_id: Optional[str]
    chat_id: Optional[str]
    chat_type: Optional[str]
    message_type: Optional[str]
    content: str
    text: Optional[str]
    sender_open_id: Optional[str]
    sender_user_id: Optional[str]
    sender_union_id: Optional[str]
    raw: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_context(cls, context: EventContext) -> "P2ImMessageReceiveV1":
        event = _as_mapping(context.event)
        message = _as_mapping(event.get("message"))
        sender = _as_mapping(event.get("sender"))
        sender_id = _as_mapping(sender.get("sender_id"))
        content = _as_optional_str(message.get("content")) or ""
        text = _extract_text_content(content)
        return cls(
            event_id=context.envelope.event_id,
            create_time=context.envelope.create_time,
            tenant_key=context.envelope.tenant_key,
            app_id=context.envelope.app_id,
            message_id=_as_optional_str(message.get("message_id")),
            chat_id=_as_optional_str(message.get("chat_id")),
            chat_type=_as_optional_str(message.get("chat_type")),
            message_type=_as_optional_str(message.get("message_type")),
            content=content,
            text=text,
            sender_open_id=_as_optional_str(sender_id.get("open_id")),
            sender_user_id=_as_optional_str(sender_id.get("user_id")),
            sender_union_id=_as_optional_str(sender_id.get("union_id")),
            raw=dict(context.payload),
        )


@dataclass(frozen=True)
class P2ApplicationBotMenuV6:
    event_id: Optional[str]
    create_time: Optional[str]
    tenant_key: Optional[str]
    app_id: Optional[str]
    event_key: Optional[str]
    operator_open_id: Optional[str]
    operator_user_id: Optional[str]
    operator_union_id: Optional[str]
    raw: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_context(cls, context: EventContext) -> "P2ApplicationBotMenuV6":
        event = _as_mapping(context.event)
        operator = _as_mapping(event.get("operator"))
        return cls(
            event_id=context.envelope.event_id,
            create_time=context.envelope.create_time,
            tenant_key=context.envelope.tenant_key,
            app_id=context.envelope.app_id,
            event_key=_as_optional_str(event.get("event_key")),
            operator_open_id=_as_optional_str(operator.get("open_id")),
            operator_user_id=_as_optional_str(operator.get("user_id")),
            operator_union_id=_as_optional_str(operator.get("union_id")),
            raw=dict(context.payload),
        )


@dataclass(frozen=True)
class P2CardActionTrigger:
    event_id: Optional[str]
    tenant_key: Optional[str]
    app_id: Optional[str]
    open_id: Optional[str]
    user_id: Optional[str]
    action_tag: Optional[str]
    action_value: Mapping[str, Any]
    raw: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_context(cls, context: EventContext) -> "P2CardActionTrigger":
        event = _as_mapping(context.event)
        operator = _as_mapping(event.get("operator"))
        action = _as_mapping(event.get("action"))
        action_value = _as_mapping(action.get("value"))
        return cls(
            event_id=context.envelope.event_id,
            tenant_key=context.envelope.tenant_key,
            app_id=context.envelope.app_id,
            open_id=_as_optional_str(operator.get("open_id")),
            user_id=_as_optional_str(operator.get("user_id")),
            action_tag=_as_optional_str(action.get("tag")),
            action_value=dict(action_value),
            raw=dict(context.payload),
        )


@dataclass(frozen=True)
class P2URLPreviewGet:
    event_id: Optional[str]
    tenant_key: Optional[str]
    app_id: Optional[str]
    open_id: Optional[str]
    user_id: Optional[str]
    url: Optional[str]
    preview_token: Optional[str]
    open_chat_id: Optional[str]
    open_message_id: Optional[str]
    raw: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_context(cls, context: EventContext) -> "P2URLPreviewGet":
        event = _as_mapping(context.event)
        operator = _as_mapping(event.get("operator"))
        details = _as_mapping(event.get("context"))
        return cls(
            event_id=context.envelope.event_id,
            tenant_key=context.envelope.tenant_key,
            app_id=context.envelope.app_id,
            open_id=_as_optional_str(operator.get("open_id")),
            user_id=_as_optional_str(operator.get("user_id")),
            url=_as_optional_str(details.get("url")),
            preview_token=_as_optional_str(details.get("preview_token")),
            open_chat_id=_as_optional_str(details.get("open_chat_id")),
            open_message_id=_as_optional_str(details.get("open_message_id")),
            raw=dict(context.payload),
        )


@dataclass(frozen=True)
class P1CustomizedEvent:
    event_type: str
    event_id: Optional[str]
    token: Optional[str]
    tenant_key: Optional[str]
    app_id: Optional[str]
    ts: Optional[str]
    event: Mapping[str, Any]
    raw: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_context(cls, context: EventContext) -> "P1CustomizedEvent":
        event = _as_mapping(context.event)
        return cls(
            event_type=context.envelope.event_type,
            event_id=context.envelope.event_id,
            token=context.envelope.token,
            tenant_key=context.envelope.tenant_key,
            app_id=context.envelope.app_id,
            ts=context.envelope.create_time,
            event=dict(event),
            raw=dict(context.payload),
        )


@dataclass(frozen=True)
class P2DriveFileBitableRecordChangedV1:
    event_id: Optional[str]
    create_time: Optional[str]
    tenant_key: Optional[str]
    app_id: Optional[str]
    file_type: Optional[str]
    file_token: Optional[str]
    table_id: Optional[str]
    revision: Optional[int]
    operator_union_id: Optional[str]
    operator_user_id: Optional[str]
    operator_open_id: Optional[str]
    action_list: list[Mapping[str, Any]] = field(default_factory=list)
    subscriber_id_list: list[Mapping[str, Any]] = field(default_factory=list)
    update_time: Optional[int] = None
    raw: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_context(cls, context: EventContext) -> "P2DriveFileBitableRecordChangedV1":
        event = _as_mapping(context.event)
        operator = _as_mapping(event.get("operator_id"))
        return cls(
            event_id=context.envelope.event_id,
            create_time=context.envelope.create_time,
            tenant_key=context.envelope.tenant_key,
            app_id=context.envelope.app_id,
            file_type=_as_optional_str(event.get("file_type")),
            file_token=_as_optional_str(event.get("file_token")),
            table_id=_as_optional_str(event.get("table_id")),
            revision=_as_optional_int(event.get("revision")),
            operator_union_id=_as_optional_str(operator.get("union_id")),
            operator_user_id=_as_optional_str(operator.get("user_id")),
            operator_open_id=_as_optional_str(operator.get("open_id")),
            action_list=_as_mapping_list(event.get("action_list")),
            subscriber_id_list=_as_mapping_list(event.get("subscriber_id_list")),
            update_time=_as_optional_int(event.get("update_time")),
            raw=dict(context.payload),
        )


@dataclass(frozen=True)
class P2DriveFileBitableFieldChangedV1:
    event_id: Optional[str]
    create_time: Optional[str]
    tenant_key: Optional[str]
    app_id: Optional[str]
    file_type: Optional[str]
    file_token: Optional[str]
    table_id: Optional[str]
    revision: Optional[int]
    operator_union_id: Optional[str]
    operator_user_id: Optional[str]
    operator_open_id: Optional[str]
    action_list: list[Mapping[str, Any]] = field(default_factory=list)
    subscriber_id_list: list[Mapping[str, Any]] = field(default_factory=list)
    update_time: Optional[int] = None
    raw: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_context(cls, context: EventContext) -> "P2DriveFileBitableFieldChangedV1":
        event = _as_mapping(context.event)
        operator = _as_mapping(event.get("operator_id"))
        return cls(
            event_id=context.envelope.event_id,
            create_time=context.envelope.create_time,
            tenant_key=context.envelope.tenant_key,
            app_id=context.envelope.app_id,
            file_type=_as_optional_str(event.get("file_type")),
            file_token=_as_optional_str(event.get("file_token")),
            table_id=_as_optional_str(event.get("table_id")),
            revision=_as_optional_int(event.get("revision")),
            operator_union_id=_as_optional_str(operator.get("union_id")),
            operator_user_id=_as_optional_str(operator.get("user_id")),
            operator_open_id=_as_optional_str(operator.get("open_id")),
            action_list=_as_mapping_list(event.get("action_list")),
            subscriber_id_list=_as_mapping_list(event.get("subscriber_id_list")),
            update_time=_as_optional_int(event.get("update_time")),
            raw=dict(context.payload),
        )


def _extract_text_content(content: str) -> Optional[str]:
    if not content:
        return None
    try:
        content_json = json.loads(content)
    except json.JSONDecodeError:
        return None
    if not isinstance(content_json, dict):
        return None
    text = content_json.get("text")
    if isinstance(text, str):
        return text
    return None
