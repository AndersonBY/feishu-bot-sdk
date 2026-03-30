from __future__ import annotations

from typing import Any

import click

from ..commands.config import (
    _cmd_config_init,
    _cmd_config_list_profiles,
    _cmd_config_migrate_token_store,
    _cmd_config_remove_profile,
    _cmd_config_set_default_as,
    _cmd_config_set_default_profile,
    _cmd_config_show,
)
from ..context import build_cli_context, with_runtime_options


@click.group("config", help="Manage CLI profiles, secrets, and defaults")
def config_group() -> None:
    pass


@config_group.command("init")
@click.option("--set-default", is_flag=True)
@click.option("--app-secret-stdin", is_flag=True)
@click.option("--app-secret-file")
@click.option("--default-as", "default_as")
@with_runtime_options
def config_init(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    args = cli_ctx.build_args(group="config", **params)
    cli_ctx.emit(_cmd_config_init(args), cli_args=args)


@config_group.command("show")
@with_runtime_options
def config_show(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    args = cli_ctx.build_args(group="config", **params)
    cli_ctx.emit(_cmd_config_show(args), cli_args=args)


@config_group.command("list-profiles")
@with_runtime_options
def config_list_profiles(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    args = cli_ctx.build_args(group="config", **params)
    cli_ctx.emit(_cmd_config_list_profiles(args), cli_args=args)


@config_group.command("set-default-profile")
@click.argument("profile_name")
@with_runtime_options
def config_set_default_profile(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    args = cli_ctx.build_args(group="config", **params)
    cli_ctx.emit(_cmd_config_set_default_profile(args), cli_args=args)


@config_group.command("set-default-as")
@click.option("--as", "as_value", required=True, type=click.Choice(["user", "bot", "auto"]))
@with_runtime_options(include_identity=False)
def config_set_default_as(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    args = cli_ctx.build_args(group="config", **params)
    cli_ctx.emit(_cmd_config_set_default_as(args), cli_args=args)


@config_group.command("remove-profile")
@click.argument("profile_name", required=False)
@click.option("--keep-secret", is_flag=True)
@with_runtime_options
def config_remove_profile(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    args = cli_ctx.build_args(group="config", **params)
    cli_ctx.emit(_cmd_config_remove_profile(args), cli_args=args)


@config_group.command("migrate-token-store")
@click.option("--source-path")
@click.option("--default-profile")
@click.option("--only-profile", "only_profiles", multiple=True)
@click.option("--app-secret-stdin", is_flag=True)
@click.option("--app-secret-file")
@with_runtime_options
def config_migrate_token_store(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    args = cli_ctx.build_args(group="config", **params)
    cli_ctx.emit(_cmd_config_migrate_token_store(args), cli_args=args)


__all__ = ["config_group"]
