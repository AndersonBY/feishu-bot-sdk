import inspect
from typing import Any, Awaitable, Callable, TypeVar

from .handlers import EventHandlerRegistry
from .models import (
    P1CustomizedEvent,
    P2ApplicationBotMenuV6,
    P2CardActionTrigger,
    P2DriveFileBitableFieldChangedV1,
    P2DriveFileBitableRecordChangedV1,
    P2ImMessageReceiveV1,
    P2URLPreviewGet,
)
from .types import EventContext

TModel = TypeVar("TModel")


class FeishuEventRegistry(EventHandlerRegistry):
    def on_im_message_receive(
        self,
        handler: Callable[[P2ImMessageReceiveV1], Any] | Callable[[P2ImMessageReceiveV1], Awaitable[Any]],
    ) -> "FeishuEventRegistry":
        self._register_typed(
            "im.message.receive_v1",
            P2ImMessageReceiveV1.from_context,
            handler,
        )
        return self

    def on_bot_menu(
        self,
        handler: Callable[[P2ApplicationBotMenuV6], Any] | Callable[[P2ApplicationBotMenuV6], Awaitable[Any]],
    ) -> "FeishuEventRegistry":
        self._register_typed(
            "application.bot.menu_v6",
            P2ApplicationBotMenuV6.from_context,
            handler,
        )
        return self

    def on_card_action_trigger(
        self,
        handler: Callable[[P2CardActionTrigger], Any] | Callable[[P2CardActionTrigger], Awaitable[Any]],
    ) -> "FeishuEventRegistry":
        self._register_typed(
            "card.action.trigger",
            P2CardActionTrigger.from_context,
            handler,
        )
        return self

    def on_url_preview_get(
        self,
        handler: Callable[[P2URLPreviewGet], Any] | Callable[[P2URLPreviewGet], Awaitable[Any]],
    ) -> "FeishuEventRegistry":
        self._register_typed(
            "url.preview.get",
            P2URLPreviewGet.from_context,
            handler,
        )
        return self

    def on_bitable_record_changed(
        self,
        handler: Callable[[P2DriveFileBitableRecordChangedV1], Any]
        | Callable[[P2DriveFileBitableRecordChangedV1], Awaitable[Any]],
    ) -> "FeishuEventRegistry":
        self._register_typed(
            "drive.file.bitable_record_changed_v1",
            P2DriveFileBitableRecordChangedV1.from_context,
            handler,
        )
        return self

    def on_bitable_field_changed(
        self,
        handler: Callable[[P2DriveFileBitableFieldChangedV1], Any]
        | Callable[[P2DriveFileBitableFieldChangedV1], Awaitable[Any]],
    ) -> "FeishuEventRegistry":
        self._register_typed(
            "drive.file.bitable_field_changed_v1",
            P2DriveFileBitableFieldChangedV1.from_context,
            handler,
        )
        return self

    def on_p1_customized_event(
        self,
        event_type: str,
        handler: Callable[[P1CustomizedEvent], Any] | Callable[[P1CustomizedEvent], Awaitable[Any]],
    ) -> "FeishuEventRegistry":
        self._register_typed(event_type, P1CustomizedEvent.from_context, handler)
        return self

    def _register_typed(
        self,
        event_type: str,
        parser: Callable[[EventContext], TModel],
        handler: Callable[[TModel], Any] | Callable[[TModel], Awaitable[Any]],
    ) -> None:
        wrapped = _wrap_typed_handler(parser, handler)
        self.register(event_type, wrapped)


def _wrap_typed_handler(
    parser: Callable[[EventContext], TModel],
    handler: Callable[[TModel], Any] | Callable[[TModel], Awaitable[Any]],
):
    if inspect.iscoroutinefunction(handler):

        async def _wrapped(context: EventContext) -> Any:
            parsed = parser(context)
            return await handler(parsed)

        return _wrapped

    def _wrapped(context: EventContext) -> Any:
        parsed = parser(context)
        return handler(parsed)

    return _wrapped
