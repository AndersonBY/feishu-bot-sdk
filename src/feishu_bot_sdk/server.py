import asyncio
import inspect
import signal
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, Optional, Protocol, TypeVar, cast

from .events import (
    EventContext,
    FeishuEventRegistry,
    P1CustomizedEvent,
    P2ApplicationBotMenuV6,
    P2CardActionTrigger,
    P2DriveFileBitableFieldChangedV1,
    P2DriveFileBitableRecordChangedV1,
    P2ImMessageReceiveV1,
    P2URLPreviewGet,
)
from .ws import AsyncLongConnectionClient, HeartbeatConfig, ReconnectPolicy


class _ManagedWSClient(Protocol):
    async def start(self) -> None:
        ...

    async def stop(self) -> None:
        ...


THandlerInput = TypeVar("THandlerInput")
TSyncHandler = Callable[[THandlerInput], Any]
TAsyncHandler = Callable[[THandlerInput], Awaitable[Any]]


@dataclass(frozen=True)
class FeishuBotServerStatus:
    running: bool
    started_at: Optional[float]
    stopped_at: Optional[float]
    last_event_at: Optional[float]
    last_event_type: Optional[str]
    total_events: int
    event_counts: Dict[str, int] = field(default_factory=dict)
    last_error: Optional[str] = None


class FeishuBotServer:
    def __init__(
        self,
        *,
        app_id: str,
        app_secret: str,
        domain: str = "https://open.feishu.cn",
        timeout_seconds: float = 30.0,
        reconnect_policy: Optional[ReconnectPolicy] = None,
        heartbeat: Optional[HeartbeatConfig] = None,
        registry: Optional[FeishuEventRegistry] = None,
        ws_client_factory: Optional[Callable[[FeishuEventRegistry], _ManagedWSClient]] = None,
    ) -> None:
        self._app_id = app_id
        self._app_secret = app_secret
        self._domain = domain
        self._timeout_seconds = timeout_seconds
        self._reconnect_policy = reconnect_policy
        self._heartbeat = heartbeat
        self._registry = registry or FeishuEventRegistry()
        self._ws_client_factory = ws_client_factory or self._default_ws_client_factory

        self._lock = asyncio.Lock()
        self._client: Optional[_ManagedWSClient] = None
        self._run_task: Optional[asyncio.Task[None]] = None

        self._started_at: Optional[float] = None
        self._stopped_at: Optional[float] = None
        self._last_event_at: Optional[float] = None
        self._last_event_type: Optional[str] = None
        self._total_events = 0
        self._event_counts: Dict[str, int] = {}
        self._last_error: Optional[str] = None

    @property
    def registry(self) -> FeishuEventRegistry:
        return self._registry

    @property
    def is_running(self) -> bool:
        return self._run_task is not None and not self._run_task.done()

    def on_event(
        self,
        event_type: str,
        handler: TSyncHandler[EventContext] | TAsyncHandler[EventContext],
    ) -> "FeishuBotServer":
        wrapped = self._wrap_handler(event_type, handler)
        self._registry.register(event_type, wrapped)
        return self

    def on_default(
        self,
        handler: TSyncHandler[EventContext] | TAsyncHandler[EventContext],
    ) -> "FeishuBotServer":
        wrapped = self._wrap_handler("*", handler)
        self._registry.register_default(wrapped)
        return self

    def on_im_message_receive(
        self,
        handler: TSyncHandler[P2ImMessageReceiveV1] | TAsyncHandler[P2ImMessageReceiveV1],
    ) -> "FeishuBotServer":
        self._registry.on_im_message_receive(self._wrap_handler("im.message.receive_v1", handler))
        return self

    def on_bot_menu(
        self,
        handler: TSyncHandler[P2ApplicationBotMenuV6] | TAsyncHandler[P2ApplicationBotMenuV6],
    ) -> "FeishuBotServer":
        self._registry.on_bot_menu(self._wrap_handler("application.bot.menu_v6", handler))
        return self

    def on_card_action_trigger(
        self,
        handler: TSyncHandler[P2CardActionTrigger] | TAsyncHandler[P2CardActionTrigger],
    ) -> "FeishuBotServer":
        self._registry.on_card_action_trigger(self._wrap_handler("card.action.trigger", handler))
        return self

    def on_url_preview_get(
        self,
        handler: TSyncHandler[P2URLPreviewGet] | TAsyncHandler[P2URLPreviewGet],
    ) -> "FeishuBotServer":
        self._registry.on_url_preview_get(self._wrap_handler("url.preview.get", handler))
        return self

    def on_bitable_record_changed(
        self,
        handler: TSyncHandler[P2DriveFileBitableRecordChangedV1]
        | TAsyncHandler[P2DriveFileBitableRecordChangedV1],
    ) -> "FeishuBotServer":
        self._registry.on_bitable_record_changed(
            self._wrap_handler("drive.file.bitable_record_changed_v1", handler)
        )
        return self

    def on_bitable_field_changed(
        self,
        handler: TSyncHandler[P2DriveFileBitableFieldChangedV1]
        | TAsyncHandler[P2DriveFileBitableFieldChangedV1],
    ) -> "FeishuBotServer":
        self._registry.on_bitable_field_changed(
            self._wrap_handler("drive.file.bitable_field_changed_v1", handler)
        )
        return self

    def on_p1_customized_event(
        self,
        event_type: str,
        handler: TSyncHandler[P1CustomizedEvent] | TAsyncHandler[P1CustomizedEvent],
    ) -> "FeishuBotServer":
        self._registry.on_p1_customized_event(event_type, self._wrap_handler(event_type, handler))
        return self

    def unregister(self, event_type: str) -> None:
        self._registry.unregister(event_type)

    def status(self) -> FeishuBotServerStatus:
        return FeishuBotServerStatus(
            running=self.is_running,
            started_at=self._started_at,
            stopped_at=self._stopped_at,
            last_event_at=self._last_event_at,
            last_event_type=self._last_event_type,
            total_events=self._total_events,
            event_counts=dict(self._event_counts),
            last_error=self._last_error,
        )

    async def start(self) -> None:
        async with self._lock:
            if self.is_running:
                return
            self._last_error = None
            self._started_at = time.time()
            self._stopped_at = None
            self._client = self._ws_client_factory(self._registry)
            self._run_task = asyncio.create_task(self._run_client())

    async def stop(self) -> None:
        async with self._lock:
            client = self._client
            task = self._run_task
        if client is not None:
            await client.stop()
        if task is not None:
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
        async with self._lock:
            self._client = None
            self._run_task = None
            self._stopped_at = time.time()

    async def wait(self) -> None:
        task = self._run_task
        if task is None:
            return
        await task

    async def run_forever(self, *, handle_signals: bool = True) -> None:
        await self.start()
        task = self._run_task
        if task is None:
            return
        if not handle_signals:
            await task
            return

        loop = asyncio.get_running_loop()
        stop_event = asyncio.Event()
        handlers = _install_signal_handlers(loop, stop_event)
        waiter = asyncio.create_task(stop_event.wait())
        try:
            done, _ = await asyncio.wait({task, waiter}, return_when=asyncio.FIRST_COMPLETED)
            if waiter in done:
                await self.stop()
                return
            await task
        finally:
            waiter.cancel()
            _restore_signal_handlers(handlers)

    def run(self, *, handle_signals: bool = True) -> None:
        asyncio.run(self.run_forever(handle_signals=handle_signals))

    def _default_ws_client_factory(self, registry: FeishuEventRegistry) -> _ManagedWSClient:
        return cast(
            _ManagedWSClient,
            AsyncLongConnectionClient(
                app_id=self._app_id,
                app_secret=self._app_secret,
                handler_registry=registry,
                domain=self._domain,
                timeout_seconds=self._timeout_seconds,
                reconnect_policy=self._reconnect_policy,
                heartbeat=self._heartbeat,
            ),
        )

    async def _run_client(self) -> None:
        client = self._client
        if client is None:
            return
        try:
            await client.start()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._last_error = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            self._stopped_at = time.time()

    def _record_event(self, event_type: str) -> None:
        now = time.time()
        self._last_event_at = now
        self._last_event_type = event_type
        self._total_events += 1
        self._event_counts[event_type] = self._event_counts.get(event_type, 0) + 1

    def _wrap_handler(
        self,
        expected_event_type: str,
        handler: TSyncHandler[THandlerInput] | TAsyncHandler[THandlerInput],
    ) -> TSyncHandler[THandlerInput] | TAsyncHandler[THandlerInput]:
        if inspect.iscoroutinefunction(handler):

            async def _wrapped(payload: THandlerInput) -> Any:
                event_type = _resolve_event_type(expected_event_type, payload)
                self._record_event(event_type)
                async_handler = cast(TAsyncHandler[THandlerInput], handler)
                return await async_handler(payload)

            return _wrapped

        def _wrapped(payload: THandlerInput) -> Any:
            event_type = _resolve_event_type(expected_event_type, payload)
            self._record_event(event_type)
            sync_handler = cast(TSyncHandler[THandlerInput], handler)
            return sync_handler(payload)

        return _wrapped


def _resolve_event_type(expected_event_type: str, payload: Any) -> str:
    if expected_event_type != "*":
        return expected_event_type
    if isinstance(payload, EventContext):
        event_type = payload.envelope.event_type
        if event_type:
            return event_type
    return expected_event_type


def _install_signal_handlers(
    loop: asyncio.AbstractEventLoop,
    stop_event: asyncio.Event,
) -> list[tuple[int, Any]]:
    installed: list[tuple[int, Any]] = []
    for sig in _supported_signals():
        try:
            previous = signal.getsignal(sig)

            def _handler(_signum: int, _frame: Any) -> None:
                loop.call_soon_threadsafe(stop_event.set)

            signal.signal(sig, _handler)
            installed.append((sig, previous))
        except (ValueError, OSError, RuntimeError):
            continue
    return installed


def _restore_signal_handlers(installed: list[tuple[int, Any]]) -> None:
    for sig, previous in installed:
        try:
            signal.signal(sig, previous)
        except (ValueError, OSError, RuntimeError):
            continue


def _supported_signals() -> list[int]:
    supported: list[int] = []
    for name in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, name, None)
        if isinstance(sig, int):
            supported.append(sig)
    return supported

