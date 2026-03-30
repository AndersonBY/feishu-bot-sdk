from __future__ import annotations

from typing import Any

import click

from ..commands.eventing import (
    _cmd_server_run,
    _cmd_server_start,
    _cmd_server_status,
    _cmd_server_stop,
)
from ..context import build_cli_context, with_runtime_options


@click.group("server", help="Feishu bot long-connection server for persistent event handling")
def server_group() -> None:
    pass


@server_group.command("run")
@click.option("--domain", help="Open platform domain, default: https://open.feishu.cn")
@click.option("--event-type", "event_types", multiple=True, help="Register specific event type(s), can be repeated")
@click.option("--print-payload", is_flag=True, help="Print full payload for each event")
@click.option("--output-file", help="Append events as JSON lines to file")
@click.option("--max-events", type=int, help="Auto stop after receiving N events")
@click.option("--no-handle-signals", is_flag=True, help="Disable SIGINT/SIGTERM handling in server.run()")
@with_runtime_options
def server_run(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    args = cli_ctx.build_args(group="server", server_command="run", **params)
    cli_ctx.emit(_cmd_server_run(args), cli_args=args)


@server_group.command("start")
@click.option("--domain", help="Open platform domain, default: https://open.feishu.cn")
@click.option("--event-type", "event_types", multiple=True, help="Register specific event type(s), can be repeated")
@click.option("--print-payload", is_flag=True, help="Print full payload for each event")
@click.option("--output-file", help="Append events as JSON lines to file")
@click.option("--max-events", type=int, help="Auto stop after receiving N events")
@click.option("--pid-file", default=".feishu_server.pid", show_default=True, help="PID file path")
@click.option("--log-file", help="Redirect server stdout/stderr to this file")
@with_runtime_options
def server_start(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    args = cli_ctx.build_args(group="server", server_command="start", **params)
    cli_ctx.emit(_cmd_server_start(args), cli_args=args)


@server_group.command("status")
@click.option("--pid-file", default=".feishu_server.pid", show_default=True, help="PID file path")
@with_runtime_options
def server_status(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    args = cli_ctx.build_args(group="server", server_command="status", **params)
    cli_ctx.emit(_cmd_server_status(args), cli_args=args)


@server_group.command("stop")
@click.option("--pid-file", default=".feishu_server.pid", show_default=True, help="PID file path")
@with_runtime_options
def server_stop(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    args = cli_ctx.build_args(group="server", server_command="stop", **params)
    cli_ctx.emit(_cmd_server_stop(args), cli_args=args)


__all__ = ["server_group"]
