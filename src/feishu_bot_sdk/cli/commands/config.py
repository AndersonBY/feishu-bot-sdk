from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Mapping

from ...token_store import default_token_store_path
from ..runtime import (
    CLIProfile,
    default_cli_config_path,
    load_token_store_profiles,
    load_cli_config,
    make_profile,
    migrate_token_store_to_cli_config,
    resolve_cli_profile_name,
    resolve_secret_store,
    save_cli_config,
)


def _cmd_config_init(args: argparse.Namespace) -> Mapping[str, Any]:
    config = load_cli_config()
    profile_name = resolve_cli_profile_name(getattr(args, "profile", None), config=config)
    app_id = getattr(args, "app_id", None)
    if not app_id:
        raise ValueError("config init requires --app-id")
    secret_value = _read_app_secret(args)
    if not secret_value:
        raise ValueError(
            "config init requires app secret via --app-secret-stdin, --app-secret-file, or --app-secret"
        )

    secret_store = resolve_secret_store()
    secret_ref = secret_store.put(f"profile:{profile_name}:app_secret", secret_value)

    existing = config.profile(profile_name)
    profile = make_profile(
        profile_name,
        app_id=str(app_id),
        app_secret_ref=secret_ref,
        auth_mode=getattr(args, "auth_mode", None) or (existing.auth_mode if existing else None),
        base_url=getattr(args, "base_url", None) or (existing.base_url if existing else None),
        timeout_seconds=getattr(args, "timeout", None) or (existing.timeout_seconds if existing else None),
        default_identity=existing.default_identity if existing else None,
        token_store_path=getattr(args, "token_store", None) or (existing.token_store_path if existing else None),
    )
    updated = config.with_profile(
        profile,
        set_default=bool(getattr(args, "set_default", False)) or not config.profiles,
    )
    config_path = save_cli_config(updated)
    return _profile_payload(
        profile,
        config_path=config_path,
        default_profile=updated.default_profile,
        secret_store_path=secret_store.store_path,
        secret_key_path=secret_store.key_path,
    )


def _cmd_config_show(args: argparse.Namespace) -> Mapping[str, Any]:
    config = load_cli_config()
    profile_name = resolve_cli_profile_name(getattr(args, "profile", None), config=config)
    profile = config.profile(profile_name)
    if profile is None:
        raise ValueError(f"profile {profile_name!r} is not configured")
    secret_store = resolve_secret_store()
    return _profile_payload(
        profile,
        config_path=default_cli_config_path(),
        default_profile=config.default_profile,
        secret_store_path=secret_store.store_path,
        secret_key_path=secret_store.key_path,
    )


def _cmd_config_list_profiles(_args: argparse.Namespace) -> Mapping[str, Any]:
    config = load_cli_config()
    items: list[dict[str, Any]] = []
    for name in sorted(config.profiles):
        profile = config.profiles[name]
        items.append(
            {
                "profile": name,
                "default": name == config.default_profile,
                "app_id": profile.app_id,
                "auth_mode": profile.auth_mode,
                "base_url": profile.base_url,
                "has_app_secret": profile.app_secret_ref is not None,
            }
        )
    return {
        "default_profile": config.default_profile,
        "count": len(items),
        "profiles": items,
    }


def _cmd_config_set_default_profile(args: argparse.Namespace) -> Mapping[str, Any]:
    profile_name = str(args.profile_name)
    config = load_cli_config()
    if config.profile(profile_name) is None:
        raise ValueError(f"profile {profile_name!r} does not exist")
    updated = config.with_default_profile(profile_name)
    config_path = save_cli_config(updated)
    return {
        "profile": profile_name,
        "default_profile": updated.default_profile,
        "config_path": str(config_path),
    }


def _cmd_config_remove_profile(args: argparse.Namespace) -> Mapping[str, Any]:
    config = load_cli_config()
    profile_name = str(
        getattr(args, "profile_name", None)
        or resolve_cli_profile_name(getattr(args, "profile", None), config=config)
    )
    profile = config.profile(profile_name)
    if profile is None:
        raise ValueError(f"profile {profile_name!r} does not exist")
    removed_secret = False
    if not bool(getattr(args, "keep_secret", False)) and profile.app_secret_ref is not None:
        removed_secret = resolve_secret_store().delete(profile.app_secret_ref)
    updated = config.without_profile(profile_name)
    config_path = save_cli_config(updated)
    return {
        "profile": profile_name,
        "deleted": True,
        "removed_secret": removed_secret,
        "default_profile": updated.default_profile,
        "config_path": str(config_path),
    }


def _cmd_config_migrate_token_store(args: argparse.Namespace) -> Mapping[str, Any]:
    source_path = Path(str(getattr(args, "source_path", None) or default_token_store_path()))
    importable_profiles = load_token_store_profiles(source_path)
    if not importable_profiles:
        raise ValueError(f"token store {source_path} does not contain any importable profiles")

    config = load_cli_config()
    token_store_path = Path(str(getattr(args, "token_store", None) or source_path))
    selected_profiles = [
        str(item).strip()
        for item in (getattr(args, "only_profiles", None) or [])
        if str(item).strip()
    ]
    target_profiles = selected_profiles or sorted(importable_profiles)
    missing_profiles = [name for name in target_profiles if name not in importable_profiles]
    if missing_profiles:
        missing_text = ", ".join(sorted(missing_profiles))
        raise ValueError(f"requested token store profiles do not exist: {missing_text}")

    shared_secret_value = _read_optional_app_secret(args)
    secret_store = resolve_secret_store()
    secret_refs: dict[str, Any] = {}
    if shared_secret_value:
        for profile_name in target_profiles:
            secret_refs[profile_name] = secret_store.put(
                f"profile:{profile_name}:app_secret",
                shared_secret_value,
            )
    updated, result = migrate_token_store_to_cli_config(
        config,
        source_path=source_path,
        token_store_path=token_store_path,
        default_profile=getattr(args, "default_profile", None),
        only_profiles=selected_profiles,
        app_id=getattr(args, "app_id", None),
        app_secret_refs=secret_refs,
        auth_mode=getattr(args, "auth_mode", None),
        base_url=getattr(args, "base_url", None),
        timeout_seconds=getattr(args, "timeout", None),
    )
    migrated_profiles = []
    missing_app_credentials: list[str] = []
    for name in result.imported_profiles:
        profile = updated.profile(name)
        if profile is None:
            continue
        has_app_secret = profile.app_secret_ref is not None
        if not profile.app_id or not has_app_secret:
            missing_app_credentials.append(name)
        migrated_profiles.append(
            {
                "profile": name,
                "app_id": profile.app_id,
                "auth_mode": profile.auth_mode,
                "base_url": profile.base_url,
                "token_store_path": profile.token_store_path,
                "has_app_secret": has_app_secret,
            }
        )
    return {
        "source_path": str(result.source_path),
        "token_store_path": str(result.token_store_path),
        "config_path": str(result.config_path),
        "default_profile": result.default_profile,
        "imported_count": len(result.imported_profiles),
        "imported_profiles": migrated_profiles,
        "missing_app_credentials_profiles": missing_app_credentials,
        "secret_store_path": str(secret_store.store_path),
        "secret_key_path": str(secret_store.key_path),
    }


def _read_app_secret(args: argparse.Namespace) -> str:
    stdin_enabled = bool(getattr(args, "app_secret_stdin", False))
    file_path = getattr(args, "app_secret_file", None)
    direct = getattr(args, "app_secret", None)

    if sum(1 for item in (stdin_enabled, bool(file_path), bool(direct)) if item) > 1:
        raise ValueError("use only one of --app-secret-stdin, --app-secret-file, or --app-secret")
    if stdin_enabled:
        value = sys.stdin.read().strip()
        if not value:
            raise ValueError("stdin did not provide an app secret")
        return value
    if file_path:
        value = Path(str(file_path)).read_text(encoding="utf-8").strip()
        if not value:
            raise ValueError("app secret file is empty")
        return value
    if direct:
        return str(direct).strip()
    return ""


def _read_optional_app_secret(args: argparse.Namespace) -> str:
    try:
        return _read_app_secret(args)
    except ValueError as exc:
        if "use only one of" in str(exc):
            raise
        return ""


def _profile_payload(
    profile: CLIProfile,
    *,
    config_path: Path,
    default_profile: str,
    secret_store_path: Path,
    secret_key_path: Path,
) -> Mapping[str, Any]:
    return {
        "profile": profile.name,
        "default": profile.name == default_profile,
        "default_profile": default_profile,
        "config_path": str(config_path),
        "app_id": profile.app_id,
        "auth_mode": profile.auth_mode,
        "base_url": profile.base_url,
        "timeout_seconds": profile.timeout_seconds,
        "default_identity": profile.default_identity,
        "token_store_path": profile.token_store_path,
        "has_app_secret": profile.app_secret_ref is not None,
        "app_secret_backend": profile.app_secret_ref.backend if profile.app_secret_ref else None,
        "secret_store_path": str(secret_store_path),
        "secret_key_path": str(secret_key_path),
        "updated_at": profile.updated_at,
    }


__all__ = [name for name in globals() if name.startswith("_cmd_")]
