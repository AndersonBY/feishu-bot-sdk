import json
from typing import Any, Dict, Mapping

from ..events import EventHandlerRegistry, build_event_context
from .constants import MESSAGE_TYPE_CARD, MESSAGE_TYPE_EVENT
from .errors import WSHandlerError


class WSDispatcher:
    def __init__(self, handler_registry: EventHandlerRegistry) -> None:
        self._handlers = handler_registry

    def dispatch(self, payload: bytes, *, message_type: str) -> Any:
        payload_dict = _decode_payload(payload)
        is_callback = message_type == MESSAGE_TYPE_CARD
        if message_type not in (MESSAGE_TYPE_EVENT, MESSAGE_TYPE_CARD):
            return None
        context = build_event_context(payload_dict, is_callback=is_callback)
        if not self._handlers.has_handler(context.envelope.event_type):
            raise WSHandlerError(f"event handler not found: {context.envelope.event_type}")
        return self._handlers.dispatch(context)


def _decode_payload(payload: bytes) -> Dict[str, Any]:
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WSHandlerError("ws payload is not valid json") from exc
    if not isinstance(data, Mapping):
        raise WSHandlerError("ws payload must be a json object")
    return {str(key): value for key, value in data.items()}
