from __future__ import annotations

import argparse

from ..commands import (
    _cmd_server_run,
    _cmd_server_start,
    _cmd_server_status,
    _cmd_server_stop,
    _cmd_webhook_challenge,
    _cmd_webhook_decode,
    _cmd_webhook_parse,
    _cmd_webhook_serve,
    _cmd_webhook_verify_signature,
    _cmd_ws_endpoint,
    _cmd_ws_run,
)
from .common import _add_webhook_body_args

def _build_webhook_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    shared: argparse.ArgumentParser,
) -> None:
    webhook_parser = subparsers.add_parser("webhook", help="Webhook utility commands")
    webhook_sub = webhook_parser.add_subparsers(dest="webhook_command")
    webhook_sub.required = True

    decode = webhook_sub.add_parser("decode", help="Decode webhook body (supports encrypted payload)", parents=[shared])
    _add_webhook_body_args(decode)
    decode.add_argument("--encrypt-key", help="Encrypt key for encrypted payload")
    decode.set_defaults(handler=_cmd_webhook_decode)

    verify = webhook_sub.add_parser("verify-signature", help="Verify webhook signature headers", parents=[shared])
    verify.add_argument("--headers-json", help="Headers JSON object string")
    verify.add_argument("--headers-file", help="Headers JSON file path")
    verify.add_argument("--headers-stdin", action="store_true", help="Read headers JSON from stdin")
    _add_webhook_body_args(verify)
    verify.add_argument("--encrypt-key", help="Encrypt key used for signature")
    verify.add_argument(
        "--tolerance-seconds",
        type=float,
        default=300.0,
        help="Timestamp tolerance seconds (default: 300)",
    )
    verify.set_defaults(handler=_cmd_webhook_verify_signature)

    challenge = webhook_sub.add_parser("challenge", help="Build challenge response payload", parents=[shared])
    challenge.add_argument("--challenge", required=True, help="Challenge string")
    challenge.set_defaults(handler=_cmd_webhook_challenge)

    parse = webhook_sub.add_parser("parse", help="Parse webhook envelope", parents=[shared])
    _add_webhook_body_args(parse)
    parse.add_argument("--encrypt-key", help="Encrypt key for encrypted payload")
    parse.add_argument(
        "--is-callback",
        action="store_true",
        help="Parse as callback payload",
    )
    parse.add_argument(
        "--include-payload",
        action="store_true",
        help="Include decoded payload in output",
    )
    parse.set_defaults(handler=_cmd_webhook_parse)

    serve = webhook_sub.add_parser("serve", help="Run local webhook HTTP server", parents=[shared])
    serve.add_argument("--host", default="127.0.0.1", help="Listen host (default: 127.0.0.1)")
    serve.add_argument("--port", type=int, default=8000, help="Listen port (default: 8000)")
    serve.add_argument("--path", default="/webhook/feishu", help="Webhook path (default: /webhook/feishu)")
    serve.add_argument("--encrypt-key", help="Encrypt key for encrypted payload/signature")
    serve.add_argument(
        "--verification-token",
        help="Verification token for token check",
    )
    serve.add_argument(
        "--is-callback",
        action="store_true",
        help="Treat incoming payload as callback mode",
    )
    serve.add_argument(
        "--no-verify-signatures",
        action="store_true",
        help="Disable signature verification",
    )
    serve.add_argument(
        "--timestamp-tolerance-seconds",
        type=float,
        default=300.0,
        help="Signature timestamp tolerance in seconds (default: 300)",
    )
    serve.add_argument(
        "--print-payload",
        action="store_true",
        help="Print full payload for each event",
    )
    serve.add_argument(
        "--output-file",
        help="Append events as JSON lines to file",
    )
    serve.add_argument(
        "--event-type",
        action="append",
        dest="event_types",
        help="Register specific event type(s), can be repeated",
    )
    serve.add_argument(
        "--max-requests",
        type=int,
        help="Auto stop after handling N POST requests",
    )
    serve.set_defaults(handler=_cmd_webhook_serve)

def _build_ws_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    shared: argparse.ArgumentParser,
) -> None:
    ws_parser = subparsers.add_parser("ws", help="WebSocket long-connection utilities")
    ws_sub = ws_parser.add_subparsers(dest="ws_command")
    ws_sub.required = True

    endpoint = ws_sub.add_parser("endpoint", help="Fetch long-connection endpoint", parents=[shared])
    endpoint.add_argument(
        "--domain",
        help="Open platform domain, default: https://open.feishu.cn",
    )
    endpoint.set_defaults(handler=_cmd_ws_endpoint)

    run = ws_sub.add_parser("run", help="Run low-level WS listener", parents=[shared])
    run.add_argument(
        "--domain",
        help="Open platform domain, default: https://open.feishu.cn",
    )
    run.add_argument(
        "--event-type",
        action="append",
        dest="event_types",
        help="Register specific event type(s), can be repeated",
    )
    run.add_argument(
        "--print-payload",
        action="store_true",
        help="Print full payload for each event",
    )
    run.add_argument(
        "--output-file",
        help="Append events as JSON lines to file",
    )
    run.add_argument(
        "--max-events",
        type=int,
        help="Auto stop after receiving N events",
    )
    run.add_argument(
        "--duration-seconds",
        type=float,
        help="Auto stop after duration seconds",
    )
    run.set_defaults(handler=_cmd_ws_run)

def _build_server_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    shared: argparse.ArgumentParser,
) -> None:
    server_parser = subparsers.add_parser("server", help="Feishu bot long-connection server")
    server_sub = server_parser.add_subparsers(dest="server_command")
    server_sub.required = True

    run = server_sub.add_parser("run", help="Run long-connection server", parents=[shared])
    run.add_argument(
        "--domain",
        help="Open platform domain, default: https://open.feishu.cn",
    )
    run.add_argument(
        "--event-type",
        action="append",
        dest="event_types",
        help="Register specific event type(s), can be repeated",
    )
    run.add_argument(
        "--print-payload",
        action="store_true",
        help="Print full payload for each event",
    )
    run.add_argument(
        "--output-file",
        help="Append events as JSON lines to file",
    )
    run.add_argument(
        "--max-events",
        type=int,
        help="Auto stop after receiving N events",
    )
    run.add_argument(
        "--no-handle-signals",
        action="store_true",
        help="Disable SIGINT/SIGTERM handling in server.run()",
    )
    run.set_defaults(handler=_cmd_server_run)

    start = server_sub.add_parser("start", help="Start server in background", parents=[shared])
    start.add_argument(
        "--domain",
        help="Open platform domain, default: https://open.feishu.cn",
    )
    start.add_argument(
        "--event-type",
        action="append",
        dest="event_types",
        help="Register specific event type(s), can be repeated",
    )
    start.add_argument(
        "--print-payload",
        action="store_true",
        help="Print full payload for each event",
    )
    start.add_argument(
        "--output-file",
        help="Append events as JSON lines to file",
    )
    start.add_argument(
        "--max-events",
        type=int,
        help="Auto stop after receiving N events",
    )
    start.add_argument(
        "--pid-file",
        default=".feishu_server.pid",
        help="PID file path (default: .feishu_server.pid)",
    )
    start.add_argument(
        "--log-file",
        help="Redirect server stdout/stderr to this file",
    )
    start.set_defaults(handler=_cmd_server_start)

    status = server_sub.add_parser("status", help="Check background server status", parents=[shared])
    status.add_argument(
        "--pid-file",
        default=".feishu_server.pid",
        help="PID file path (default: .feishu_server.pid)",
    )
    status.set_defaults(handler=_cmd_server_status)

    stop = server_sub.add_parser("stop", help="Stop background server", parents=[shared])
    stop.add_argument(
        "--pid-file",
        default=".feishu_server.pid",
        help="PID file path (default: .feishu_server.pid)",
    )
    stop.set_defaults(handler=_cmd_server_stop)
