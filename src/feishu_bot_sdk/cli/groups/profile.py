from __future__ import annotations

import time
from dataclasses import replace
from typing import Any, Mapping

import click

from ..commands.config import _read_app_secret
from ..context import build_cli_context, with_runtime_options
from ..runtime import (
    CLIProfile,
    load_cli_config,
    resolve_secret_store,
    save_cli_config,
)


@click.group("profile", help="Manage lark-style CLI profiles")
def profile_group() -> None:
    pass


@profile_group.command("list")
@with_runtime_options
def profile_list(**kwargs: Any) -> None:
    cli_ctx, _params = build_cli_context(kwargs)
    config = load_cli_config()
    rows = [_profile_list_item(profile, active=name == config.default_profile) for name, profile in sorted(config.profiles.items())]
    cli_ctx.emit(rows, cli_args=cli_ctx.build_args(group="profile", command="list"))


@profile_group.command("add")
@click.option("--name", required=True, help="Profile name")
@click.option("--app-secret-stdin", is_flag=True, help="Read app secret from stdin")
@click.option("--brand", default="feishu", show_default=True, type=click.Choice(["feishu", "lark"]))
@click.option("--lang", default="zh", show_default=True, type=click.Choice(["zh", "en"]))
@click.option("--use", "use_after", is_flag=True, help="Switch to this profile after adding")
@with_runtime_options
def profile_add(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    config = load_cli_config()
    name = _normalize_profile_name(params.get("name"))
    if config.profile(name) is not None:
        raise ValueError(f"profile {name!r} already exists")
    app_id = cli_ctx.app_id
    if not app_id:
        raise ValueError("profile add requires --app-id")
    for existing_name, existing in config.profiles.items():
        if existing.app_id == app_id:
            raise ValueError(f"app-id {app_id!r} is already used by profile {existing_name!r}")

    args = cli_ctx.build_args(
        app_secret_stdin=bool(params.get("app_secret_stdin")),
        app_secret=cli_ctx.app_secret,
        app_secret_file=None,
    )
    secret_value = _read_app_secret(args)
    secret_ref = resolve_secret_store().put(f"profile:{name}:app_secret", secret_value)
    profile = CLIProfile(
        name=name,
        app_id=app_id,
        app_secret_ref=secret_ref,
        brand=str(params.get("brand") or "feishu"),
        lang=str(params.get("lang") or "zh"),
        auth_mode=cli_ctx.build_args().auth_mode,
        base_url=cli_ctx.base_url,
        timeout_seconds=cli_ctx.timeout,
        default_as=cli_ctx.as_type if cli_ctx.as_type != "auto" else None,
        token_store_path=cli_ctx.token_store,
        updated_at=time.time(),
    )
    updated = config.with_profile(profile, set_default=bool(params.get("use_after")) or not config.profiles)
    config_path = save_cli_config(updated)
    payload = _profile_payload(profile, config=updated)
    payload["config_path"] = str(config_path)
    cli_ctx.emit(payload, cli_args=cli_ctx.build_args(group="profile", command="add"))


@profile_group.command("use")
@click.argument("name")
@with_runtime_options
def profile_use(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    config = load_cli_config()
    requested_name = _normalize_profile_name(params.get("name"))
    name = config.previous_profile if requested_name == "-" else requested_name
    if not name:
        raise ValueError("no previous profile to switch back to")
    profile = config.profile(name)
    if profile is None:
        raise ValueError(f"profile {name!r} does not exist")
    previous_profile = config.default_profile if config.default_profile != name else config.previous_profile
    updated = config.with_default_profile(name, remember_previous=True)
    config_path = save_cli_config(updated)
    payload = _profile_payload(profile, config=updated)
    payload["previous_profile"] = previous_profile
    payload["config_path"] = str(config_path)
    cli_ctx.emit(payload, cli_args=cli_ctx.build_args(group="profile", command="use"))


@profile_group.command("remove")
@click.argument("name")
@click.option("--keep-secret", is_flag=True)
@with_runtime_options
def profile_remove(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    config = load_cli_config()
    name = _normalize_profile_name(params.get("name"))
    profile = config.profile(name)
    if profile is None:
        raise ValueError(f"profile {name!r} does not exist")
    removed_secret = False
    if not bool(params.get("keep_secret")) and profile.app_secret_ref is not None:
        removed_secret = resolve_secret_store().delete(profile.app_secret_ref)
    updated = config.without_profile(name)
    config_path = save_cli_config(updated)
    cli_ctx.emit(
        {
            "name": name,
            "profile": name,
            "deleted": True,
            "removed_secret": removed_secret,
            "default_profile": updated.default_profile,
            "config_path": str(config_path),
        },
        cli_args=cli_ctx.build_args(group="profile", command="remove"),
    )


@profile_group.command("rename")
@click.argument("old")
@click.argument("new")
@with_runtime_options
def profile_rename(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    config = load_cli_config()
    old_name = _normalize_profile_name(params.get("old"))
    new_name = _normalize_profile_name(params.get("new"))
    profile = config.profile(old_name)
    if profile is None:
        raise ValueError(f"profile {old_name!r} does not exist")
    if config.profile(new_name) is not None:
        raise ValueError(f"profile {new_name!r} already exists")
    profiles = dict(config.profiles)
    profiles.pop(old_name)
    renamed = replace(profile, name=new_name, updated_at=time.time())
    profiles[new_name] = renamed
    default_profile = new_name if config.default_profile == old_name else config.default_profile
    previous_profile = config.previous_profile
    if previous_profile == old_name:
        previous_profile = new_name
    updated = type(config)(
        version=config.version,
        default_profile=default_profile,
        previous_profile=previous_profile,
        strict_mode=config.strict_mode,
        profiles=profiles,
    )
    config_path = save_cli_config(updated)
    payload = _profile_payload(renamed, config=updated)
    payload["old_name"] = old_name
    payload["config_path"] = str(config_path)
    cli_ctx.emit(payload, cli_args=cli_ctx.build_args(group="profile", command="rename"))


def _profile_payload(profile: CLIProfile, *, config: Any) -> dict[str, Any]:
    return {
        "name": profile.name,
        "profile": profile.name,
        "appId": profile.app_id,
        "app_id": profile.app_id,
        "brand": profile.brand or "feishu",
        "lang": profile.lang,
        "active": profile.name == config.default_profile,
        "default": profile.name == config.default_profile,
        "default_profile": config.default_profile,
        "default_as": profile.default_as,
        "strict_mode": profile.strict_mode,
        "has_app_secret": profile.app_secret_ref is not None,
        "binding": dict(profile.binding) if isinstance(profile.binding, Mapping) else None,
    }


def _profile_list_item(profile: CLIProfile, *, active: bool) -> dict[str, Any]:
    return {
        "name": profile.name,
        "profile": profile.name,
        "appId": profile.app_id,
        "app_id": profile.app_id,
        "brand": profile.brand or "feishu",
        "active": active,
        "default": active,
        "default_as": profile.default_as,
        "strict_mode": profile.strict_mode,
        "has_app_secret": profile.app_secret_ref is not None,
    }


def _normalize_profile_name(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError("profile name cannot be empty")
    if any(ch.isspace() for ch in text):
        raise ValueError("profile name cannot contain whitespace")
    return text


__all__ = ["profile_group"]
