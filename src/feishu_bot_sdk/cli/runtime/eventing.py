from __future__ import annotations

import asyncio
import contextlib
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping

from ...events import EventContext, FeishuEventRegistry
from ...webhook import WebhookReceiver
from ...ws import AsyncLongConnectionClient

from .input import _read_request_body
from .output import (
    _build_event_view,
    _emit_event,
    _print_runtime_error,
    _print_runtime_status,
    _to_jsonable,
)


def _cli_override(name: str, default: Any) -> Any:
    cli_module = sys.modules.get("feishu_bot_sdk.cli")
    if cli_module is None:
        return default
    return getattr(cli_module, name, default)


def _serve_webhook_http(
    *,
    receiver: WebhookReceiver,
    host: str,
    port: int,
    path: str,
    output_format: str,
    max_requests: int | None,
) -> None:
    state: dict[str, int] = {"requests": 0}

    class _Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            request_path = self.path.split("?", 1)[0]
            if request_path != path:
                self._send_json(404, {"ok": False, "error": "not found"})
                return

            raw_body = _read_request_body(self.headers, self.rfile)
            headers = {str(k): str(v) for k, v in self.headers.items()}
            try:
                response = receiver.handle(headers, raw_body)
                self._send_json(200, response)
            except Exception as exc:
                error_payload = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
                self._send_json(400, error_payload)
                _print_runtime_error(error_payload["error"], output_format=output_format)
            finally:
                state["requests"] = int(state["requests"]) + 1
                if max_requests is not None and int(state["requests"]) >= max_requests:
                    threading.Thread(target=self.server.shutdown, daemon=True).start()

        def do_GET(self) -> None:  # noqa: N802
            self._send_json(200, {"ok": True, "path": path})

        def log_message(self, format: str, *args: object) -> None:  # noqa: A003
            return

        def _send_json(self, status_code: int, payload: Mapping[str, Any]) -> None:
            body = json.dumps(_to_jsonable(payload), ensure_ascii=False).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    startup_payload = {"status": "listening", "host": host, "port": port, "path": path}
    _print_runtime_status(startup_payload, output_format=output_format)
    with ThreadingHTTPServer((host, port), _Handler) as server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
    _print_runtime_status({"status": "stopped", "requests": int(state["requests"])}, output_format=output_format)


async def _run_ws_listener(
    *,
    app_id: str,
    app_secret: str,
    domain: str,
    timeout_seconds: float,
    output_format: str,
    output_file: Path | None,
    print_payload: bool,
    max_events: int | None,
    duration_seconds: float | None,
    event_types: list[str],
) -> int:
    registry = FeishuEventRegistry()
    state: dict[str, Any] = {"events": 0, "stop_requested": False}
    client: AsyncLongConnectionClient | None = None

    def _request_stop() -> None:
        if client is None:
            return
        if bool(state["stop_requested"]):
            return
        state["stop_requested"] = True
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(client.stop())
        except RuntimeError:
            pass

    def _on_event(ctx: EventContext) -> None:
        event = _build_event_view(ctx, include_payload=print_payload)
        _emit_event(event, output_format=output_format, output_file=output_file)
        state["events"] = int(state["events"]) + 1
        if max_events is not None and int(state["events"]) >= max_events:
            _request_stop()

    if event_types:
        for event_type in event_types:
            registry.register(event_type, _on_event)
    else:
        registry.register_default(_on_event)

    client_cls = _cli_override("AsyncLongConnectionClient", AsyncLongConnectionClient)
    client = client_cls(
        app_id=app_id,
        app_secret=app_secret,
        handler_registry=registry,
        domain=domain,
        timeout_seconds=timeout_seconds,
    )

    run_task = asyncio.create_task(client.start())
    try:
        if duration_seconds is not None:
            try:
                await asyncio.wait_for(run_task, timeout=duration_seconds)
            except asyncio.TimeoutError:
                _request_stop()
                try:
                    await asyncio.wait_for(run_task, timeout=max(timeout_seconds, 5.0))
                except asyncio.CancelledError:
                    pass
        else:
            try:
                await run_task
            except asyncio.CancelledError:
                if not bool(state["stop_requested"]):
                    raise
    finally:
        if not run_task.done():
            await client.stop()
            with contextlib.suppress(Exception):
                await run_task
    return int(state["events"])


__all__ = [name for name in globals() if not name.startswith("__")]
