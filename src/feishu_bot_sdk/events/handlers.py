import inspect
import threading
from typing import Any, Awaitable, Callable, Dict, Optional, Union

from .types import EventContext

SyncEventHandler = Callable[[EventContext], Any]
AsyncEventHandler = Callable[[EventContext], Awaitable[Any]]
_RegisteredHandler = Union[SyncEventHandler, AsyncEventHandler]


def is_async_handler(handler: _RegisteredHandler) -> bool:
    return inspect.iscoroutinefunction(handler)


class EventHandlerRegistry:
    def __init__(self) -> None:
        self._handlers: Dict[str, _RegisteredHandler] = {}
        self._default_handler: Optional[_RegisteredHandler] = None
        self._lock = threading.RLock()

    def register(self, event_type: str, handler: _RegisteredHandler) -> None:
        if not event_type:
            raise ValueError("event_type must not be empty")
        with self._lock:
            self._handlers[event_type] = handler

    def register_default(self, handler: _RegisteredHandler) -> None:
        with self._lock:
            self._default_handler = handler

    def unregister(self, event_type: str) -> None:
        with self._lock:
            self._handlers.pop(event_type, None)

    def get_handler(self, event_type: str) -> Optional[_RegisteredHandler]:
        with self._lock:
            handler = self._handlers.get(event_type)
            if handler is not None:
                return handler
            return self._default_handler

    def has_handler(self, event_type: str) -> bool:
        return self.get_handler(event_type) is not None

    def dispatch(self, context: EventContext) -> Any:
        handler = self.get_handler(context.envelope.event_type)
        if handler is None:
            raise KeyError(f"event handler not found: {context.envelope.event_type}")
        if is_async_handler(handler):
            raise RuntimeError("async handler is not supported by dispatch(), use adispatch()")
        return handler(context)

    async def adispatch(self, context: EventContext) -> Any:
        handler = self.get_handler(context.envelope.event_type)
        if handler is None:
            raise KeyError(f"event handler not found: {context.envelope.event_type}")
        result = handler(context)
        if inspect.isawaitable(result):
            return await result
        return result
