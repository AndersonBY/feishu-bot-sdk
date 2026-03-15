from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from ...response import DataResponse


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


def _as_optional_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    return None


def _extract_message_payload(
    response: Mapping[str, Any],
    *,
    use_first_item: bool,
) -> Mapping[str, Any]:
    data = DataResponse.from_raw(response)
    if use_first_item:
        items = data.get("items")
        if isinstance(items, list) and items:
            first = items[0]
            if isinstance(first, Mapping):
                return dict(first)
    return data


@dataclass(frozen=True)
class Message:
    message_id: Optional[str]
    chat_id: Optional[str]
    root_id: Optional[str]
    parent_id: Optional[str]
    thread_id: Optional[str]
    msg_type: Optional[str]
    create_time: Optional[str]
    update_time: Optional[str]
    deleted: Optional[bool]
    updated: Optional[bool]
    raw: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_raw(cls, payload: Mapping[str, Any]) -> "Message":
        normalized = _as_mapping(payload)
        return cls(
            message_id=_as_optional_str(normalized.get("message_id")),
            chat_id=_as_optional_str(normalized.get("chat_id")),
            root_id=_as_optional_str(normalized.get("root_id")),
            parent_id=_as_optional_str(normalized.get("parent_id")),
            thread_id=_as_optional_str(normalized.get("thread_id")),
            msg_type=_as_optional_str(normalized.get("msg_type")),
            create_time=_as_optional_str(normalized.get("create_time")),
            update_time=_as_optional_str(normalized.get("update_time")),
            deleted=_as_optional_bool(normalized.get("deleted")),
            updated=_as_optional_bool(normalized.get("updated")),
            raw=dict(normalized),
        )


@dataclass(frozen=True)
class MessageResponse:
    code: int
    msg: Optional[str]
    message: Optional[Message]
    raw: Mapping[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.code == 0

    @property
    def message_id(self) -> Optional[str]:
        return self.message.message_id if self.message is not None else None

    @classmethod
    def from_raw(
        cls,
        payload: Mapping[str, Any],
        *,
        use_first_item: bool = False,
    ) -> "MessageResponse":
        message_payload = _extract_message_payload(payload, use_first_item=use_first_item)
        message = Message.from_raw(message_payload) if message_payload else None
        code_raw = payload.get("code")
        code = code_raw if isinstance(code_raw, int) else 0
        return cls(
            code=code,
            msg=_as_optional_str(payload.get("msg")),
            message=message,
            raw=dict(payload),
        )


__all__ = ["Message", "MessageResponse"]
