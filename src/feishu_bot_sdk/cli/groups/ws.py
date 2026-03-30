from __future__ import annotations

from typing import Any

import click

from ..commands.eventing import (
    _cmd_ws_endpoint,
    _cmd_ws_run,
)
from ..context import build_cli_context, with_runtime_options


@click.group("ws", help="WebSocket long-connection utilities for Feishu event subscription")
def ws_group() -> None:
    pass


@ws_group.command("endpoint")
@click.option("--domain", help="Open platform domain, default: https://open.feishu.cn")
@with_runtime_options
def ws_endpoint(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    args = cli_ctx.build_args(group="ws", ws_command="endpoint", **params)
    cli_ctx.emit(_cmd_ws_endpoint(args), cli_args=args)


@ws_group.command("run")
@click.option("--domain", help="Open platform domain, default: https://open.feishu.cn")
@click.option("--event-type", "event_types", multiple=True, help="Register specific event type(s), can be repeated")
@click.option("--print-payload", is_flag=True, help="Print full payload for each event")
@click.option("--output-file", help="Append events as JSON lines to file")
@click.option("--max-events", type=int, help="Auto stop after receiving N events")
@click.option("--duration-seconds", type=float, help="Auto stop after duration seconds")
@with_runtime_options
def ws_run(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    args = cli_ctx.build_args(group="ws", ws_command="run", **params)
    cli_ctx.emit(_cmd_ws_run(args), cli_args=args)


__all__ = ["ws_group"]
