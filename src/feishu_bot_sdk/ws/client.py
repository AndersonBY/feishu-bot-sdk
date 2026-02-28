import asyncio
import base64
import contextlib
import json
import time
from typing import Any, Mapping, Optional

import websockets
from websockets.exceptions import ConnectionClosed

from ..events import EventHandlerRegistry
from ..http_client import AsyncJsonHttpClient
from .constants import (
    FRAME_TYPE_CONTROL,
    FRAME_TYPE_DATA,
    HEADER_BIZ_RT,
    HEADER_MESSAGE_ID,
    HEADER_SEQ,
    HEADER_SUM,
    HEADER_TYPE,
    MESSAGE_TYPE_PONG,
    WS_DEFAULT_DOMAIN,
)
from .dispatcher import WSDispatcher
from .endpoint import WSRemoteConfig, fetch_ws_endpoint_async
from .errors import WSConnectionError
from .frames import (
    FrameCombiner,
    add_frame_header,
    frame_headers_to_dict,
    new_ping_frame,
    parse_frame,
    serialize_frame,
)
from .heartbeat import HeartbeatConfig
from .reconnect import ReconnectPolicy


class AsyncLongConnectionClient:
    def __init__(
        self,
        *,
        app_id: str,
        app_secret: str,
        handler_registry: EventHandlerRegistry,
        domain: str = WS_DEFAULT_DOMAIN,
        timeout_seconds: float = 30.0,
        reconnect_policy: Optional[ReconnectPolicy] = None,
        heartbeat: Optional[HeartbeatConfig] = None,
        http_client: Optional[AsyncJsonHttpClient] = None,
    ) -> None:
        self._app_id = app_id
        self._app_secret = app_secret
        self._domain = domain
        self._timeout_seconds = timeout_seconds
        self._http = http_client or AsyncJsonHttpClient(timeout_seconds=timeout_seconds)
        self._dispatcher = WSDispatcher(handler_registry)
        self._reconnect_policy = reconnect_policy or ReconnectPolicy()
        self._heartbeat = heartbeat or HeartbeatConfig()
        self._combiner = FrameCombiner()

        self._service_id = 0
        self._conn = None
        self._running = False
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        self._running = True
        self._stop_event.clear()
        attempt = 0
        while self._running and not self._stop_event.is_set():
            try:
                await self._run_single_connection()
                attempt = 0
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                if not self._running or self._stop_event.is_set():
                    break
                if not self._reconnect_policy.should_retry(attempt):
                    raise WSConnectionError("long connection exhausted retries") from exc
                delay = self._reconnect_policy.get_delay_seconds(attempt)
                attempt += 1
                await asyncio.sleep(delay)

    async def stop(self) -> None:
        self._running = False
        self._stop_event.set()
        if self._conn is not None:
            await self._conn.close()
        await self._http.aclose()

    async def _run_single_connection(self) -> None:
        endpoint = await fetch_ws_endpoint_async(
            app_id=self._app_id,
            app_secret=self._app_secret,
            domain=self._domain,
            timeout_seconds=self._timeout_seconds,
            http_client=self._http,
        )
        self._apply_remote_config(endpoint.remote_config)
        self._service_id = int(endpoint.service_id or 0)

        async with websockets.connect(endpoint.url, max_size=None) as conn:
            self._conn = conn
            ping_task = asyncio.create_task(self._heartbeat_loop())
            try:
                await self._receive_loop()
            finally:
                ping_task.cancel()
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await ping_task
                self._conn = None

    async def _receive_loop(self) -> None:
        if self._conn is None:
            return
        while self._running and not self._stop_event.is_set():
            try:
                message = await self._conn.recv()
            except ConnectionClosed:
                raise WSConnectionError("long connection closed by server")
            if isinstance(message, str):
                message_bytes = message.encode("utf-8")
            else:
                message_bytes = message
            await self._handle_message(message_bytes)

    async def _heartbeat_loop(self) -> None:
        while self._running and not self._stop_event.is_set():
            if self._conn is None:
                return
            frame = new_ping_frame(self._service_id)
            await self._conn.send(serialize_frame(frame))
            await asyncio.sleep(self._heartbeat.interval_seconds)

    async def _handle_message(self, raw_message: bytes) -> None:
        frame = parse_frame(raw_message)
        if int(frame.method) == FRAME_TYPE_CONTROL:
            await self._handle_control_frame(frame)
            return
        if int(frame.method) == FRAME_TYPE_DATA:
            await self._handle_data_frame(frame)

    async def _handle_control_frame(self, frame: Any) -> None:
        headers = frame_headers_to_dict(frame)
        if headers.get(HEADER_TYPE) != MESSAGE_TYPE_PONG:
            return
        self._heartbeat.last_pong_at = time.time()
        if frame.payload:
            self._apply_remote_config_from_payload(frame.payload)

    async def _handle_data_frame(self, frame: Any) -> None:
        headers = frame_headers_to_dict(frame)
        payload = frame.payload or b""

        total = _safe_int(headers.get(HEADER_SUM), default=1)
        if total > 1:
            message_id = headers.get(HEADER_MESSAGE_ID) or ""
            seq = _safe_int(headers.get(HEADER_SEQ), default=0)
            merged = self._combiner.append(message_id, payload, total=total, seq=seq)
            if merged is None:
                return
            payload = merged

        start_ms = int(time.time() * 1000)
        response_payload: bytes
        try:
            result = self._dispatcher.dispatch(payload, message_type=headers.get(HEADER_TYPE, ""))
            response_payload = _build_response_payload(200, result)
        except Exception:
            response_payload = _build_response_payload(500, None)

        duration_ms = int(time.time() * 1000) - start_ms
        add_frame_header(frame, HEADER_BIZ_RT, str(duration_ms))
        frame.payload = response_payload
        await self._send_frame(frame)

    async def _send_frame(self, frame: Any) -> None:
        if self._conn is None:
            raise WSConnectionError("connection is not ready")
        await self._conn.send(serialize_frame(frame))

    def _apply_remote_config(self, remote_config: WSRemoteConfig) -> None:
        self._reconnect_policy.retry_count = remote_config.reconnect_count
        self._reconnect_policy.interval_seconds = remote_config.reconnect_interval_seconds
        self._reconnect_policy.initial_jitter_seconds = remote_config.reconnect_nonce_seconds
        self._heartbeat.update_interval(remote_config.ping_interval_seconds)

    def _apply_remote_config_from_payload(self, payload: bytes) -> None:
        try:
            data = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return
        if not isinstance(data, Mapping):
            return
        remote_config = WSRemoteConfig(
            reconnect_count=int(data.get("ReconnectCount") or self._reconnect_policy.retry_count),
            reconnect_interval_seconds=float(
                data.get("ReconnectInterval") or self._reconnect_policy.interval_seconds
            ),
            reconnect_nonce_seconds=float(
                data.get("ReconnectNonce") or self._reconnect_policy.initial_jitter_seconds
            ),
            ping_interval_seconds=float(data.get("PingInterval") or self._heartbeat.interval_seconds),
        )
        self._apply_remote_config(remote_config)


class LongConnectionClient:
    def __init__(self, **kwargs: Any) -> None:
        self._async_client = AsyncLongConnectionClient(**kwargs)

    def start(self) -> None:
        asyncio.run(self._async_client.start())

    def stop(self) -> None:
        asyncio.run(self._async_client.stop())


def _build_response_payload(code: int, result: Any) -> bytes:
    body: dict = {"code": code}
    if isinstance(result, Mapping):
        encoded = base64.b64encode(json.dumps(dict(result)).encode("utf-8")).decode("utf-8")
        body["data"] = encoded
    return json.dumps(body).encode("utf-8")


def _safe_int(value: Optional[str], *, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default
