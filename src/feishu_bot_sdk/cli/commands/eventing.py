from __future__ import annotations

import argparse
import asyncio
import os
import sys
from typing import Any, Mapping

from ...events import FeishuEventRegistry, parse_event_envelope
from ...exceptions import ConfigurationError
from ...server import FeishuBotServer
from ...webhook import WebhookReceiver, build_challenge_response, decode_webhook_body, verify_signature
from ...ws import fetch_ws_endpoint

from ..runtime import (
    _build_event_view,
    _build_server_run_subprocess_command,
    _emit_event,
    _is_process_alive,
    _normalize_server_path,
    _parse_json_object,
    _read_pid_file,
    _remove_pid_file,
    _resolve_app_credentials,
    _resolve_encrypt_key,
    _resolve_open_domain,
    _resolve_output_path,
    _resolve_pid_file,
    _resolve_raw_body,
    _resolve_timeout_seconds,
    _run_ws_listener,
    _serve_webhook_http,
    _spawn_background_process,
    _terminate_process,
    _validate_duration,
    _validate_max_events,
    _validate_positive_int,
    _write_pid_file,
)


def _cli_override(name: str, default: Any) -> Any:
    cli_module = sys.modules.get("feishu_bot_sdk.cli")
    if cli_module is None:
        return default
    return getattr(cli_module, name, default)

def _cmd_webhook_decode(args: argparse.Namespace) -> Mapping[str, Any]:
    raw_body = _resolve_raw_body(
        body_json=getattr(args, "body_json", None),
        body_file=getattr(args, "body_file", None),
        stdin_enabled=bool(getattr(args, "body_stdin", False)),
    )
    encrypt_key = _resolve_encrypt_key(args, required=False)
    return decode_webhook_body(raw_body, encrypt_key=encrypt_key)


def _cmd_webhook_verify_signature(args: argparse.Namespace) -> Mapping[str, bool]:
    headers = _parse_json_object(
        json_text=getattr(args, "headers_json", None),
        file_path=getattr(args, "headers_file", None),
        stdin_enabled=bool(getattr(args, "headers_stdin", False)),
        name="headers",
        required=True,
    )
    raw_body = _resolve_raw_body(
        body_json=getattr(args, "body_json", None),
        body_file=getattr(args, "body_file", None),
        stdin_enabled=bool(getattr(args, "body_stdin", False)),
    )
    encrypt_key = _resolve_encrypt_key(args, required=True)
    if encrypt_key is None:
        raise ConfigurationError("missing encrypt key: set FEISHU_ENCRYPT_KEY or pass --encrypt-key")
    normalized_headers = {str(key): str(value) for key, value in headers.items()}
    verify_signature(
        normalized_headers,
        raw_body,
        encrypt_key=encrypt_key,
        tolerance_seconds=float(args.tolerance_seconds),
    )
    return {"ok": True}


def _cmd_webhook_challenge(args: argparse.Namespace) -> Mapping[str, str]:
    return build_challenge_response(str(args.challenge))


def _cmd_webhook_parse(args: argparse.Namespace) -> Mapping[str, Any]:
    raw_body = _resolve_raw_body(
        body_json=getattr(args, "body_json", None),
        body_file=getattr(args, "body_file", None),
        stdin_enabled=bool(getattr(args, "body_stdin", False)),
    )
    encrypt_key = _resolve_encrypt_key(args, required=False)
    payload = decode_webhook_body(raw_body, encrypt_key=encrypt_key)
    envelope = parse_event_envelope(payload, is_callback=bool(getattr(args, "is_callback", False)))
    result: dict[str, Any] = {
        "schema": envelope.schema,
        "event_type": envelope.event_type,
        "event_id": envelope.event_id,
        "token": envelope.token,
        "tenant_key": envelope.tenant_key,
        "app_id": envelope.app_id,
        "create_time": envelope.create_time,
        "challenge": envelope.challenge,
        "is_callback": envelope.is_callback,
        "is_url_verification": envelope.is_url_verification,
    }
    if getattr(args, "include_payload", False):
        result["payload"] = payload
    return result


def _cmd_webhook_serve(args: argparse.Namespace) -> Mapping[str, Any]:
    output_format = str(args.output_format)
    output_file = _resolve_output_path(getattr(args, "output_file", None))
    max_requests = _validate_positive_int(getattr(args, "max_requests", None), name="max-requests")
    path = _normalize_server_path(str(args.path))

    registry = FeishuEventRegistry()
    event_types = [str(item) for item in list(getattr(args, "event_types", []) or [])]

    def _on_event(ctx: Any) -> None:
        event = _build_event_view(ctx, include_payload=bool(getattr(args, "print_payload", False)))
        _emit_event(event, output_format=output_format, output_file=output_file)
        return None

    if event_types:
        for event_type in event_types:
            registry.register(event_type, _on_event)
    else:
        registry.register_default(_on_event)

    receiver = WebhookReceiver(
        registry,
        encrypt_key=_resolve_encrypt_key(args, required=False),
        verification_token=(
            getattr(args, "verification_token", None)
            or os.getenv("FEISHU_VERIFICATION_TOKEN")
            or os.getenv("FEISHU_EVENT_VERIFICATION_TOKEN")
        ),
        is_callback=bool(getattr(args, "is_callback", False)),
        verify_signatures=not bool(getattr(args, "no_verify_signatures", False)),
        timestamp_tolerance_seconds=float(getattr(args, "timestamp_tolerance_seconds", 300.0)),
    )

    _cli_override("_serve_webhook_http", _serve_webhook_http)(
        receiver=receiver,
        host=str(args.host),
        port=int(args.port),
        path=path,
        output_format=output_format,
        max_requests=max_requests,
    )
    return {"ok": True}


def _cmd_ws_endpoint(args: argparse.Namespace) -> Mapping[str, Any]:
    app_id, app_secret = _resolve_app_credentials(args)
    domain = _resolve_open_domain(args)
    endpoint = _cli_override("fetch_ws_endpoint", fetch_ws_endpoint)(
        app_id=app_id,
        app_secret=app_secret,
        domain=domain,
        timeout_seconds=_resolve_timeout_seconds(args),
    )
    return {
        "url": endpoint.url,
        "device_id": endpoint.device_id,
        "service_id": endpoint.service_id,
        "remote_config": {
            "reconnect_count": endpoint.remote_config.reconnect_count,
            "reconnect_interval_seconds": endpoint.remote_config.reconnect_interval_seconds,
            "reconnect_nonce_seconds": endpoint.remote_config.reconnect_nonce_seconds,
            "ping_interval_seconds": endpoint.remote_config.ping_interval_seconds,
        },
    }


def _cmd_ws_run(args: argparse.Namespace) -> Mapping[str, Any]:
    app_id, app_secret = _resolve_app_credentials(args)
    output_file = _resolve_output_path(getattr(args, "output_file", None))
    max_events = _validate_max_events(getattr(args, "max_events", None))
    duration_seconds = _validate_duration(getattr(args, "duration_seconds", None))
    output_format = str(args.output_format)
    print_payload = bool(getattr(args, "print_payload", False))
    event_types = [str(item) for item in list(getattr(args, "event_types", []) or [])]
    events_count = asyncio.run(
        _run_ws_listener(
            app_id=app_id,
            app_secret=app_secret,
            domain=_resolve_open_domain(args),
            timeout_seconds=_resolve_timeout_seconds(args),
            output_format=output_format,
            output_file=output_file,
            print_payload=print_payload,
            max_events=max_events,
            duration_seconds=duration_seconds,
            event_types=event_types,
        )
    )
    return {"ok": True, "events": events_count}


def _cmd_server_run(args: argparse.Namespace) -> Mapping[str, Any]:
    app_id, app_secret = _resolve_app_credentials(args)
    server_cls = _cli_override("FeishuBotServer", FeishuBotServer)
    server = server_cls(
        app_id=app_id,
        app_secret=app_secret,
        domain=_resolve_open_domain(args),
        timeout_seconds=_resolve_timeout_seconds(args),
    )
    output_file = _resolve_output_path(getattr(args, "output_file", None))
    max_events = _validate_max_events(getattr(args, "max_events", None))
    state: dict[str, Any] = {"events": 0, "stop_requested": False}

    def _on_event(ctx: Any) -> None:
        event = _build_event_view(ctx, include_payload=bool(getattr(args, "print_payload", False)))
        _emit_event(
            event,
            output_format=str(args.output_format),
            output_file=output_file,
        )
        state["events"] = int(state["events"]) + 1
        if max_events is not None and int(state["events"]) >= max_events and not bool(state["stop_requested"]):
            state["stop_requested"] = True
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(server.stop())
            except RuntimeError:
                pass
        return None

    event_types = list(getattr(args, "event_types", []) or [])
    if event_types:
        for event_type in event_types:
            server.on_event(str(event_type), _on_event)
    else:
        server.on_default(_on_event)

    server.run(handle_signals=not bool(getattr(args, "no_handle_signals", False)))
    return {"ok": True, "events": int(state["events"])}


def _cmd_server_start(args: argparse.Namespace) -> Mapping[str, Any]:
    pid_file = _resolve_pid_file(getattr(args, "pid_file", None))
    existing_pid = _read_pid_file(pid_file)
    if existing_pid is not None and _cli_override("_is_process_alive", _is_process_alive)(existing_pid):
        raise ValueError(f"server is already running with pid={existing_pid} ({pid_file})")

    cmd = _build_server_run_subprocess_command(args)
    log_file = getattr(args, "log_file", None)
    process = _cli_override("_spawn_background_process", _spawn_background_process)(cmd, log_file=log_file)
    _write_pid_file(pid_file, process.pid)
    return {
        "ok": True,
        "pid": process.pid,
        "pid_file": str(pid_file),
        "log_file": str(log_file) if log_file else None,
    }


def _cmd_server_status(args: argparse.Namespace) -> Mapping[str, Any]:
    pid_file = _resolve_pid_file(getattr(args, "pid_file", None))
    pid = _read_pid_file(pid_file)
    if pid is None:
        return {"running": False, "pid_file": str(pid_file), "pid": None}
    running = _cli_override("_is_process_alive", _is_process_alive)(pid)
    return {"running": running, "pid_file": str(pid_file), "pid": pid}


def _cmd_server_stop(args: argparse.Namespace) -> Mapping[str, Any]:
    pid_file = _resolve_pid_file(getattr(args, "pid_file", None))
    pid = _read_pid_file(pid_file)
    if pid is None:
        return {"ok": False, "stopped": False, "reason": "pid file not found", "pid_file": str(pid_file)}
    if not _cli_override("_is_process_alive", _is_process_alive)(pid):
        _remove_pid_file(pid_file)
        return {"ok": True, "stopped": False, "reason": "process already exited", "pid": pid}

    _cli_override("_terminate_process", _terminate_process)(pid)
    _remove_pid_file(pid_file)
    return {"ok": True, "stopped": True, "pid": pid, "pid_file": str(pid_file)}


__all__ = [name for name in globals() if name.startswith("_cmd_")]
