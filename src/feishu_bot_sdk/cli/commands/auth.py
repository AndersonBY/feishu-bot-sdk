from __future__ import annotations

import argparse
import contextlib
import sys
import webbrowser
from typing import Any, Mapping

from ...bot import BotService

from ..runtime import (
    _build_client,
    _normalize_path,
    _parse_json_object,
    _parse_local_redirect,
    _resolve_user_token_store_context,
    _resolve_oauth_redirect_uri,
    _store_user_token,
    _wait_for_oauth_callback,
    _generate_pkce_pair,
    _generate_state,
)


def _cli_override(name: str, default: Any) -> Any:
    cli_module = sys.modules.get("feishu_bot_sdk.cli")
    if cli_module is None:
        return default
    return getattr(cli_module, name, default)


def _cmd_auth_token(args: argparse.Namespace) -> Mapping[str, Any]:
    force_user_auth = str(getattr(args, "auth_mode", "")).strip().lower() == "user"
    client = _build_client(args, force_user_auth=force_user_auth)
    return {
        "auth_mode": client.config.auth_mode,
        "access_token": client.get_access_token(),
    }


def _cmd_auth_login(args: argparse.Namespace) -> Mapping[str, Any]:
    client = _build_client(args, force_user_auth=True)
    redirect_uri = _resolve_oauth_redirect_uri(args)
    callback = _parse_local_redirect(redirect_uri)
    if callback is None:
        raise ValueError("auth login requires a localhost/127.0.0.1 redirect_uri")
    state = str(getattr(args, "state", None) or _generate_state())
    use_pkce = not bool(getattr(args, "no_pkce", False))
    code_verifier: str | None = None
    code_challenge: str | None = None
    if use_pkce:
        code_verifier, code_challenge = _generate_pkce_pair()

    authorize_url = client.build_authorize_url(
        redirect_uri=redirect_uri,
        scope=getattr(args, "scope", None),
        state=state,
        code_challenge=code_challenge,
        code_challenge_method="S256" if code_challenge else None,
    )
    no_browser = bool(getattr(args, "no_browser", False))
    if not no_browser:
        with contextlib.suppress(Exception):
            webbrowser.open(authorize_url)
    else:
        print(f"Authorize URL: {authorize_url}", file=sys.stderr, flush=True)
    callback_result = _cli_override("_wait_for_oauth_callback", _wait_for_oauth_callback)(
        host=callback["host"],
        port=callback["port"],
        path=callback["path"],
        timeout_seconds=float(getattr(args, "timeout_seconds", 180.0)),
    )
    callback_state = callback_result.get("state")
    if callback_state and callback_state != state:
        raise ValueError("oauth state mismatch")
    token = client.exchange_authorization_code(
        callback_result["code"],
        redirect_uri=redirect_uri,
        code_verifier=code_verifier,
    )
    stored = _store_user_token(args, token)
    token_payload = token.to_dict()
    token_payload.update(
        {
            "authorize_url": authorize_url,
            "profile": stored.get("profile"),
            "store_path": stored.get("store_path"),
            "stored": stored.get("stored", False),
        }
    )
    return token_payload


def _cmd_auth_refresh(args: argparse.Namespace) -> Mapping[str, Any]:
    client = _build_client(args, force_user_auth=True)
    token = client.refresh_user_access_token(refresh_token=getattr(args, "refresh_token", None))
    stored = _store_user_token(args, token)
    payload = token.to_dict()
    payload.update(
        {
            "profile": stored.get("profile"),
            "store_path": stored.get("store_path"),
            "stored": stored.get("stored", False),
        }
    )
    return payload


def _cmd_auth_whoami(args: argparse.Namespace) -> Mapping[str, Any]:
    client = _build_client(args, force_user_auth=True)
    return client.get_user_info().to_dict()


def _cmd_auth_logout(args: argparse.Namespace) -> Mapping[str, Any]:
    context = _resolve_user_token_store_context(args)
    if not context.enabled or context.store is None:
        return {
            "stored": False,
            "profile": context.profile,
            "store_path": str(context.store_path),
            "message": "token store disabled",
        }
    if bool(getattr(args, "all_profiles", False)):
        context.store.clear()
        return {
            "stored": True,
            "all_profiles": True,
            "store_path": str(context.store_path),
            "deleted": True,
        }
    deleted = context.store.delete_profile(context.profile)
    return {
        "stored": True,
        "all_profiles": False,
        "profile": context.profile,
        "store_path": str(context.store_path),
        "deleted": deleted,
    }


def _cmd_auth_request(args: argparse.Namespace) -> Mapping[str, Any]:
    params = _parse_json_object(
        json_text=getattr(args, "params_json", None),
        file_path=getattr(args, "params_file", None),
        stdin_enabled=bool(getattr(args, "params_stdin", False)),
        name="params",
        required=False,
    )
    payload = _parse_json_object(
        json_text=getattr(args, "payload_json", None),
        file_path=getattr(args, "payload_file", None),
        stdin_enabled=bool(getattr(args, "payload_stdin", False)),
        name="payload",
        required=False,
    )
    method = str(args.method).upper()
    path = _normalize_path(str(args.path))
    client = _build_client(args)
    return client.request_json(
        method,
        path,
        params=params or None,
        payload=payload or None,
    )


def _cmd_oauth_authorize_url(args: argparse.Namespace) -> Mapping[str, Any]:
    client = _build_client(args, force_user_auth=True)
    url = client.build_authorize_url(
        redirect_uri=str(args.redirect_uri),
        scope=getattr(args, "scope", None),
        state=getattr(args, "state", None),
    )
    return {"authorize_url": url}


def _cmd_oauth_exchange_code(args: argparse.Namespace) -> Any:
    client = _build_client(args, force_user_auth=True)
    token = client.exchange_authorization_code(
        str(args.code),
        grant_type=str(args.grant_type),
        redirect_uri=getattr(args, "redirect_uri", None),
        code_verifier=getattr(args, "code_verifier", None),
    )
    payload = token.to_dict()
    payload.update(_store_user_token(args, token))
    return payload


def _cmd_oauth_refresh_token(args: argparse.Namespace) -> Any:
    client = _build_client(args, force_user_auth=True)
    token = client.refresh_user_access_token(refresh_token=getattr(args, "refresh_token", None))
    payload = token.to_dict()
    payload.update(_store_user_token(args, token))
    return payload


def _cmd_oauth_user_info(args: argparse.Namespace) -> Any:
    client = _build_client(args, force_user_auth=True)
    return client.get_user_info(user_access_token=getattr(args, "user_access_token", None))


def _cmd_bot_info(args: argparse.Namespace) -> Any:
    service = BotService(_build_client(args))
    return service.get_info()


__all__ = [name for name in globals() if name.startswith("_cmd_")]
