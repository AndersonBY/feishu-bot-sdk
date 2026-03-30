from __future__ import annotations

import base64
import contextlib
import sys
import time
import webbrowser
from typing import Any

import click
import httpx

from ...token_store import StoredUserToken
from ..commands.auth import _cmd_auth_logout, _cmd_auth_refresh, _cmd_auth_token, _cmd_auth_whoami
from ..context import build_cli_context, with_runtime_options
from ..runtime import (
    _build_client,
    _generate_pkce_pair,
    _generate_state,
    _resolve_oauth_redirect_uri,
    _resolve_user_token_store_context,
    _store_user_token,
    _wait_for_oauth_callback,
)
from ..runtime.identity import available_identities
from ..runtime.scope_registry import missing_scopes, recommend_scopes


@click.group("auth", help="Manage user authorization and inspect auth state")
def auth_group() -> None:
    pass


@auth_group.command("token")
@with_runtime_options
def auth_token(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    args = cli_ctx.build_args(group="auth", auth_command="token", **params)
    cli_ctx.emit(_cmd_auth_token(args), cli_args=args)


@auth_group.command("refresh")
@click.option("--refresh-token")
@with_runtime_options(include_identity=False)
def auth_refresh(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    args = cli_ctx.build_args(group="auth", auth_command="refresh", auth_mode="user", **params)
    cli_ctx.emit(_cmd_auth_refresh(args), cli_args=args)


@auth_group.command("logout")
@click.option("--all-profiles", is_flag=True)
@with_runtime_options(include_identity=False)
def auth_logout(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    args = cli_ctx.build_args(group="auth", auth_command="logout", auth_mode="user", **params)
    cli_ctx.emit(_cmd_auth_logout(args), cli_args=args)


@auth_group.command("whoami")
@with_runtime_options(include_identity=False)
def auth_whoami(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    args = cli_ctx.build_args(group="auth", auth_command="whoami", auth_mode="user", **params)
    cli_ctx.emit(_cmd_auth_whoami(args), cli_args=args)


@auth_group.command("status")
@click.option("--verify", is_flag=True, help="Verify the current user token against the server")
@with_runtime_options(include_identity=False)
def auth_status(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    verify = bool(params.pop("verify", False))
    profile_name = cli_ctx.profile
    token_context = _resolve_user_token_store_context(cli_ctx.build_args(group="auth", auth_command="status", auth_mode="user", **params))
    stored = token_context.loaded_token
    user_available, bot_available = available_identities(cli_ctx)
    payload: dict[str, Any] = {
        "profile": token_context.profile if token_context.profile else profile_name,
        "default_as": _profile_default_as(cli_ctx.profile),
        "available_identities": [item for item, available in (("user", user_available), ("bot", bot_available)) if available],
        "user_token_status": _token_status(stored),
        "refresh_token_status": _refresh_token_status(stored),
        "granted_scopes": sorted(str(stored.scope or "").split()) if stored and stored.scope else [],
        "token_store_path": str(token_context.store_path),
        "token_store_enabled": token_context.enabled,
    }
    if verify:
        with contextlib.suppress(Exception):
            client = _build_client(cli_ctx.build_args(group="auth", auth_command="whoami", auth_mode="user"))
            payload["verified_user"] = client.get_user_info().to_dict()
    cli_ctx.emit(payload)


@auth_group.command("check")
@click.option("--scope", "scopes", multiple=True, help="Scope string or repeated values")
@click.option("--domain", "domains", multiple=True, help="Service domains to expand into recommended scopes")
@with_runtime_options(include_identity=False)
def auth_check(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    scopes = _normalize_scope_inputs(params.pop("scopes", ()))
    domains = [str(item).strip() for item in params.pop("domains", ()) if str(item).strip()]
    if not scopes and domains:
        scopes = recommend_scopes("user", services=domains)
    token_context = _resolve_user_token_store_context(cli_ctx.build_args(group="auth", auth_command="check", auth_mode="user"))
    stored = token_context.loaded_token
    granted = sorted(str(stored.scope or "").split()) if stored and stored.scope else []
    missing = missing_scopes(" ".join(granted), scopes)
    payload = {
        "granted_scopes": granted,
        "required_scopes": scopes,
        "missing_scopes": missing,
        "ok": not missing,
    }
    if missing:
        payload["hint"] = f'feishu auth login --scope "offline_access {" ".join(missing)}"'
    cli_ctx.emit(payload)


@auth_group.command("scopes")
@click.option("--domain", "domains", multiple=True, help="Service domains")
@click.option("--recommend", is_flag=True, help="Return the recommended minimum scope set")
@click.option("--identity", "identity_override", type=click.Choice(["user", "bot"]), default="user", show_default=True)
@with_runtime_options(include_identity=False)
def auth_scopes(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    domains = [str(item).strip() for item in params.pop("domains", ()) if str(item).strip()]
    recommend = bool(params.pop("recommend", False))
    identity = str(params.pop("identity_override", "user"))
    if recommend:
        scopes = recommend_scopes(identity, services=domains)
    else:
        from ..runtime.scope_registry import collect_all_scopes

        scopes = collect_all_scopes(identity, services=domains)
    cli_ctx.emit({"identity": identity, "domains": domains, "recommend": recommend, "scopes": scopes})


@auth_group.command("list")
@with_runtime_options(include_identity=False)
def auth_list(**kwargs: Any) -> None:
    cli_ctx, _ = build_cli_context(kwargs)
    from ..runtime.profiles import list_cli_profiles

    items: list[dict[str, Any]] = []
    for profile in list_cli_profiles():
        local_ctx = cli_ctx.build_args(profile=profile.name, auth_mode="user")
        token_context = _resolve_user_token_store_context(local_ctx)
        stored = token_context.loaded_token
        items.append(
            {
                "profile": profile.name,
                "app_id": profile.app_id,
                "default_as": profile.default_as,
                "user_token_status": _token_status(stored),
                "refresh_token_status": _refresh_token_status(stored),
            }
        )
    cli_ctx.emit({"count": len(items), "profiles": items})


@auth_group.command("login")
@click.option("--scope")
@click.option("--domain", "domains", multiple=True, help="Service domains to recommend scopes from")
@click.option("--recommend", is_flag=True, help="Expand --domain into the minimum recommended scope set")
@click.option("--device-code", "login_mode", flag_value="device_code", default=None, help="Use OAuth device flow")
@click.option("--localhost", "login_mode", flag_value="localhost", help="Use localhost callback flow")
@click.option("--no-wait", is_flag=True, help="Return the authorize/device payload without waiting for completion")
@click.option("--redirect-uri")
@click.option("--state")
@click.option("--timeout-seconds", type=float, default=180.0, show_default=True)
@click.option("--no-browser", is_flag=True)
@click.option("--no-pkce", is_flag=True)
@with_runtime_options(include_identity=False)
def auth_login(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    scope = str(params.pop("scope", "") or "").strip()
    domains = [str(item).strip() for item in params.pop("domains", ()) if str(item).strip()]
    recommend = bool(params.pop("recommend", False))
    if recommend and domains:
        scope = " ".join(recommend_scopes("user", services=domains))
    scope = _ensure_offline_access(scope)
    login_mode = params.pop("login_mode", None)
    if login_mode is None:
        if any(params.get(name) for name in ("redirect_uri", "state", "no_browser", "no_pkce")):
            login_mode = "localhost"
        else:
            login_mode = "device_code"
    if login_mode == "device_code":
        payload = _login_with_device_flow(cli_ctx=cli_ctx, scope=scope, **params)
    else:
        payload = _login_with_local_callback(cli_ctx=cli_ctx, scope=scope, **params)
    cli_ctx.emit(payload)


def _login_with_local_callback(
    *,
    cli_ctx: Any,
    scope: str,
    no_wait: bool,
    redirect_uri: str | None,
    state: str | None,
    timeout_seconds: float,
    no_browser: bool,
    no_pkce: bool,
    **_: Any,
) -> dict[str, Any]:
    args = cli_ctx.build_args(group="auth", auth_command="login", auth_mode="user", scope=scope, redirect_uri=redirect_uri, state=state, timeout_seconds=timeout_seconds, no_browser=no_browser, no_pkce=no_pkce)
    client = _build_client(args, force_user_auth=True)
    resolved_redirect_uri = _resolve_oauth_redirect_uri(args)
    callback = _parse_localhost_redirect(resolved_redirect_uri)
    if callback is None:
        raise ValueError("auth login requires a localhost/127.0.0.1 redirect_uri")
    state_value = state or _generate_state()
    code_verifier: str | None = None
    code_challenge: str | None = None
    if not no_pkce:
        code_verifier, code_challenge = _generate_pkce_pair()
    authorize_url = client.build_authorize_url(
        redirect_uri=resolved_redirect_uri,
        scope=scope,
        state=state_value,
        code_challenge=code_challenge,
        code_challenge_method="S256" if code_challenge else None,
    )
    if not no_browser:
        with contextlib.suppress(Exception):
            webbrowser.open(authorize_url)
    if no_wait:
        return {
            "flow": "localhost_callback",
            "authorize_url": authorize_url,
            "redirect_uri": resolved_redirect_uri,
            "state": state_value,
            "waiting": False,
        }
    cli_module = sys.modules.get("feishu_bot_sdk.cli")
    wait_for_callback = getattr(cli_module, "_wait_for_oauth_callback", _wait_for_oauth_callback)
    callback_result = wait_for_callback(
        host=callback["host"],
        port=callback["port"],
        path=callback["path"],
        timeout_seconds=timeout_seconds,
    )
    token = client.exchange_authorization_code(
        callback_result["code"],
        redirect_uri=resolved_redirect_uri,
        code_verifier=code_verifier,
    )
    stored = _store_user_token(args, token)
    payload = token.to_dict()
    payload.update(
        {
            "flow": "localhost_callback",
            "authorize_url": authorize_url,
            "profile": stored.get("profile"),
            "store_path": stored.get("store_path"),
            "stored": stored.get("stored", False),
        }
    )
    return payload


def _login_with_device_flow(
    *,
    cli_ctx: Any,
    scope: str,
    no_wait: bool,
    timeout_seconds: float,
    **_: Any,
) -> dict[str, Any]:
    args = cli_ctx.build_args(group="auth", auth_command="login", auth_mode="user")
    client = _build_client(args, force_user_auth=True)
    device_payload = _request_device_authorization(client.config.app_id, client.config.app_secret, client.config.base_url, scope)
    result = {
        "flow": "device_code",
        "scope": scope,
        **device_payload,
    }
    if no_wait:
        return result
    token_payload = _poll_device_token(
        app_id=client.config.app_id or "",
        app_secret=client.config.app_secret or "",
        base_url=client.config.base_url,
        device_code=device_payload["device_code"],
        interval=int(device_payload.get("interval") or 5),
        expires_in=int(device_payload.get("expires_in") or timeout_seconds),
    )
    if not token_payload.get("ok"):
        raise ValueError(str(token_payload.get("message") or "device authorization failed"))
    access_token = str(token_payload["access_token"])
    refresh_token = str(token_payload.get("refresh_token") or "") or None
    expires_in = int(token_payload.get("expires_in") or 7200)
    refresh_expires_in = int(token_payload.get("refresh_token_expires_in") or 604800)
    from ...feishu import OAuthUserToken

    token = OAuthUserToken(
        access_token=access_token,
        token_type=str(token_payload.get("token_type") or "Bearer"),
        expires_in=expires_in,
        refresh_token=refresh_token,
        refresh_expires_in=refresh_expires_in,
        scope=str(token_payload.get("scope") or ""),
        raw=token_payload,
    )
    stored = _store_user_token(args, token)
    payload = token.to_dict()
    payload.update(result)
    payload.update(
        {
            "profile": stored.get("profile"),
            "store_path": stored.get("store_path"),
            "stored": stored.get("stored", False),
        }
    )
    return payload


def _request_device_authorization(app_id: str | None, app_secret: str | None, base_url: str, scope: str) -> dict[str, Any]:
    if not app_id or not app_secret:
        raise ValueError("auth login --device-code requires app_id/app_secret")
    device_authorization_url, _ = _resolve_oauth_endpoints(base_url)
    basic_auth = base64.b64encode(f"{app_id}:{app_secret}".encode("utf-8")).decode("ascii")
    response = httpx.post(
        device_authorization_url,
        headers={
            "Authorization": f"Basic {basic_auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"client_id": app_id, "scope": _ensure_offline_access(scope)},
        timeout=30.0,
    )
    payload = _parse_oauth_response(response)
    return {
        "device_code": payload["device_code"],
        "user_code": payload["user_code"],
        "verification_uri": payload["verification_uri"],
        "verification_uri_complete": payload.get("verification_uri_complete") or payload["verification_uri"],
        "expires_in": int(payload.get("expires_in") or 240),
        "interval": int(payload.get("interval") or 5),
    }


def _poll_device_token(
    *,
    app_id: str,
    app_secret: str,
    base_url: str,
    device_code: str,
    interval: int,
    expires_in: int,
) -> dict[str, Any]:
    _, token_url = _resolve_oauth_endpoints(base_url)
    deadline = time.time() + max(expires_in, 60)
    current_interval = max(interval, 1)
    while time.time() < deadline:
        time.sleep(current_interval)
        response = httpx.post(
            token_url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": device_code,
                "client_id": app_id,
                "client_secret": app_secret,
            },
            timeout=30.0,
        )
        payload = _parse_oauth_response(response, allow_error=True)
        error = str(payload.get("error") or "")
        if not error and payload.get("access_token"):
            payload["ok"] = True
            return payload
        if error == "authorization_pending":
            continue
        if error == "slow_down":
            current_interval = min(current_interval + 5, 60)
            continue
        return {
            "ok": False,
            "error": error or "device_flow_error",
            "message": str(payload.get("error_description") or payload.get("message") or error or "authorization failed"),
        }
    return {"ok": False, "error": "expired_token", "message": "Authorization timed out"}


def _parse_oauth_response(response: httpx.Response, *, allow_error: bool = False) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise ValueError(f"oauth response is not valid JSON: HTTP {response.status_code}") from exc
    if not isinstance(payload, dict):
        raise ValueError("oauth response is not a JSON object")
    if response.status_code >= 400 and not allow_error:
        message = payload.get("error_description") or payload.get("error") or response.text
        raise ValueError(f"oauth request failed: {message}")
    return payload


def _resolve_oauth_endpoints(base_url: str) -> tuple[str, str]:
    if "larksuite" in base_url:
        return (
            "https://accounts.larksuite.com/oauth/v1/device_authorization",
            "https://open.larksuite.com/open-apis/authen/v2/oauth/token",
        )
    return (
        "https://accounts.feishu.cn/oauth/v1/device_authorization",
        "https://open.feishu.cn/open-apis/authen/v2/oauth/token",
    )


def _parse_localhost_redirect(redirect_uri: str) -> dict[str, Any] | None:
    from urllib.parse import urlparse

    parsed = urlparse(redirect_uri)
    if parsed.hostname not in {"127.0.0.1", "localhost"}:
        return None
    return {
        "host": parsed.hostname,
        "port": parsed.port or (443 if parsed.scheme == "https" else 80),
        "path": parsed.path or "/callback",
    }


def _ensure_offline_access(scope: str) -> str:
    items = [item for item in str(scope or "").split() if item]
    if "offline_access" not in items:
        items.insert(0, "offline_access")
    return " ".join(items)


def _token_status(token: StoredUserToken | None) -> str:
    if token is None:
        return "missing"
    if token.refresh_token and token.refresh_expires_at and token.refresh_expires_at <= time.time():
        return "expired"
    if token.expires_at and token.expires_at <= time.time():
        return "needs_refresh" if token.refresh_token else "expired"
    return "valid"


def _refresh_token_status(token: StoredUserToken | None) -> str:
    if token is None or not token.refresh_token:
        return "missing"
    if token.refresh_expires_at and token.refresh_expires_at <= time.time():
        return "expired"
    return "valid"


def _normalize_scope_inputs(values: tuple[str, ...]) -> list[str]:
    scopes: list[str] = []
    for value in values:
        scopes.extend(item for item in str(value).split() if item)
    return sorted(dict.fromkeys(scopes))


def _profile_default_as(profile_name: str | None) -> str:
    from ..runtime.profiles import resolve_cli_profile

    _, profile, _ = resolve_cli_profile(profile_name)
    return str(getattr(profile, "default_as", None) or "auto")


__all__ = ["auth_group"]
