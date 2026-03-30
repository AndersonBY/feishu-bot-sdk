from __future__ import annotations

from typing import Any

import click

from ..commands.content import _cmd_docx_create
from ..context import build_cli_context, with_runtime_options
from ..shortcuts import attach_shortcuts


@click.group("docx", help="docx document commands and shortcuts")
def docx_group() -> None:
    pass


@docx_group.command("create")
@click.option("--title", required=True, help="Document title")
@click.option("--folder-token", help="Parent folder token")
@with_runtime_options
def docx_create(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    args = cli_ctx.build_args(group="docx", docx_command="create", **params)
    cli_ctx.emit(_cmd_docx_create(args), cli_args=args)


attach_shortcuts(docx_group, "docx")


__all__ = ["docx_group"]
