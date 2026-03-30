from __future__ import annotations

from typing import Any

import click

from ..commands.eventing import (
    _cmd_webhook_challenge,
    _cmd_webhook_decode,
    _cmd_webhook_parse,
    _cmd_webhook_serve,
    _cmd_webhook_verify_signature,
)
from ..context import build_cli_context, with_runtime_options


@click.group("webhook", help="Webhook utility commands for decoding, verifying, and serving Feishu webhooks")
def webhook_group() -> None:
    pass


@webhook_group.command("decode")
@click.option("--body-json", help="Raw webhook body JSON string")
@click.option("--body-file", help="Raw webhook body file path")
@click.option("--body-stdin", is_flag=True, help="Read raw webhook body JSON from stdin")
@click.option("--encrypt-key", help="Encrypt key for encrypted payload")
@with_runtime_options
def webhook_decode(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    args = cli_ctx.build_args(group="webhook", webhook_command="decode", **params)
    cli_ctx.emit(_cmd_webhook_decode(args), cli_args=args)


@webhook_group.command("verify-signature")
@click.option("--headers-json", help="Headers JSON object string")
@click.option("--headers-file", help="Headers JSON file path")
@click.option("--headers-stdin", is_flag=True, help="Read headers JSON from stdin")
@click.option("--body-json", help="Raw webhook body JSON string")
@click.option("--body-file", help="Raw webhook body file path")
@click.option("--body-stdin", is_flag=True, help="Read raw webhook body JSON from stdin")
@click.option("--encrypt-key", help="Encrypt key used for signature")
@click.option("--tolerance-seconds", type=float, default=300.0, show_default=True, help="Timestamp tolerance seconds")
@with_runtime_options
def webhook_verify_signature(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    args = cli_ctx.build_args(group="webhook", webhook_command="verify-signature", **params)
    cli_ctx.emit(_cmd_webhook_verify_signature(args), cli_args=args)


@webhook_group.command("challenge")
@click.option("--challenge", required=True, help="Challenge string")
@with_runtime_options
def webhook_challenge(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    args = cli_ctx.build_args(group="webhook", webhook_command="challenge", **params)
    cli_ctx.emit(_cmd_webhook_challenge(args), cli_args=args)


@webhook_group.command("parse")
@click.option("--body-json", help="Raw webhook body JSON string")
@click.option("--body-file", help="Raw webhook body file path")
@click.option("--body-stdin", is_flag=True, help="Read raw webhook body JSON from stdin")
@click.option("--encrypt-key", help="Encrypt key for encrypted payload")
@click.option("--is-callback", is_flag=True, help="Parse as callback payload")
@click.option("--include-payload", is_flag=True, help="Include decoded payload in output")
@with_runtime_options
def webhook_parse(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    args = cli_ctx.build_args(group="webhook", webhook_command="parse", **params)
    cli_ctx.emit(_cmd_webhook_parse(args), cli_args=args)


@webhook_group.command("serve")
@click.option("--host", default="127.0.0.1", show_default=True, help="Listen host")
@click.option("--port", type=int, default=8000, show_default=True, help="Listen port")
@click.option("--path", default="/webhook/feishu", show_default=True, help="Webhook path")
@click.option("--encrypt-key", help="Encrypt key for encrypted payload/signature")
@click.option("--verification-token", help="Verification token for token check")
@click.option("--is-callback", is_flag=True, help="Treat incoming payload as callback mode")
@click.option("--no-verify-signatures", is_flag=True, help="Disable signature verification")
@click.option("--timestamp-tolerance-seconds", type=float, default=300.0, show_default=True, help="Signature timestamp tolerance in seconds")
@click.option("--print-payload", is_flag=True, help="Print full payload for each event")
@click.option("--output-file", help="Append events as JSON lines to file")
@click.option("--event-type", "event_types", multiple=True, help="Register specific event type(s), can be repeated")
@click.option("--max-requests", type=int, help="Auto stop after handling N POST requests")
@with_runtime_options
def webhook_serve(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    args = cli_ctx.build_args(group="webhook", webhook_command="serve", **params)
    cli_ctx.emit(_cmd_webhook_serve(args), cli_args=args)


__all__ = ["webhook_group"]
