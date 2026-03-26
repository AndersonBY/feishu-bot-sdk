from __future__ import annotations

import argparse
import base64
import contextlib
import dataclasses
import hashlib
import os
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import parse_qs, urlparse

from ...config import FeishuConfig
from ...exceptions import ConfigurationError
from ...feishu import FeishuClient
from ...token_store import StoredUserToken, TokenStore, default_token_store_path

_DEFAULT_BASE_URL = "https://open.feishu.cn/open-apis"
_DEFAULT_TIMEOUT_SECONDS = 30.0
_DEFAULT_OAUTH_CALLBACK_HOST = "127.0.0.1"
_DEFAULT_OAUTH_CALLBACK_PORT = 18080
_DEFAULT_OAUTH_CALLBACK_PATH = "/callback"
_DEFAULT_USER_TOKEN_REFRESH_BEFORE_SECONDS = 300.0


@dataclasses.dataclass(frozen=True)
class _UserTokenStoreContext:
    enabled: bool
    profile: str
    store_path: Path
    store: TokenStore | None
    from_env_or_arg: bool
    loaded_token: StoredUserToken | None

def _build_client(args: argparse.Namespace, *, force_user_auth: bool = False) -> FeishuClient:
    token_context = _resolve_user_token_store_context(args)
    config = _build_config(args, force_user_auth=force_user_auth, token_context=token_context)
    on_user_token_updated = None
    if token_context.enabled and token_context.store is not None and not token_context.from_env_or_arg:
        profile = token_context.profile
        app_id = config.app_id
        store = token_context.store

        def _persist(token: Any) -> None:
            if not hasattr(token, "access_token"):
                return
            store.save_profile(profile, _to_stored_user_token(token, app_id=app_id))

        on_user_token_updated = _persist
    return FeishuClient(config, on_user_token_updated=on_user_token_updated)


def _build_config(
    args: argparse.Namespace,
    *,
    force_user_auth: bool = False,
    token_context: _UserTokenStoreContext | None = None,
) -> FeishuConfig:
    env_app_id = os.getenv("FEISHU_APP_ID") or os.getenv("APP_ID")
    env_app_secret = os.getenv("FEISHU_APP_SECRET") or os.getenv("APP_SECRET")
    env_auth_mode = os.getenv("FEISHU_AUTH_MODE")
    env_access_token = os.getenv("FEISHU_ACCESS_TOKEN")
    env_user_access_token = os.getenv("FEISHU_USER_ACCESS_TOKEN")
    env_user_refresh_token = os.getenv("FEISHU_USER_REFRESH_TOKEN")
    env_app_access_token = os.getenv("FEISHU_APP_ACCESS_TOKEN")
    env_base_url = os.getenv("FEISHU_BASE_URL")

    app_id = env_app_id or getattr(args, "app_id", None)
    app_secret = env_app_secret or getattr(args, "app_secret", None)
    if force_user_auth:
        auth_mode = "user"
    else:
        auth_mode = (env_auth_mode or getattr(args, "auth_mode", None) or "tenant").strip().lower()
    base_url = getattr(args, "base_url", None) or env_base_url or _DEFAULT_BASE_URL
    app_access_token = env_app_access_token or getattr(args, "app_access_token", None)
    stored_token = token_context.loaded_token if token_context is not None else None
    stored_access_token = stored_token.access_token if stored_token is not None else None
    stored_refresh_token = stored_token.refresh_token if stored_token is not None else None
    user_access_from_store = (
        env_user_access_token is None
        and getattr(args, "user_access_token", None) is None
        and stored_token is not None
        and bool(stored_access_token)
    )
    user_refresh_from_store = (
        env_user_refresh_token is None
        and getattr(args, "user_refresh_token", None) is None
        and stored_token is not None
        and bool(stored_refresh_token)
    )
    user_access_token = (
        env_user_access_token
        or getattr(args, "user_access_token", None)
        or (stored_access_token if user_access_from_store else None)
    )
    user_refresh_token = (
        env_user_refresh_token
        or getattr(args, "user_refresh_token", None)
        or (stored_refresh_token if user_refresh_from_store else None)
    )
    generic_access_token = env_access_token or getattr(args, "access_token", None)
    resolved_access_token = generic_access_token
    user_access_token_expires_at = stored_token.expires_at if user_access_from_store and stored_token else None
    user_refresh_token_expires_at = (
        stored_token.refresh_expires_at if user_refresh_from_store and stored_token else None
    )
    env_refresh_before = os.getenv("FEISHU_USER_TOKEN_REFRESH_BEFORE_SECONDS")
    refresh_before_raw = env_refresh_before
    refresh_before_seconds = _DEFAULT_USER_TOKEN_REFRESH_BEFORE_SECONDS
    if refresh_before_raw:
        try:
            refresh_before_seconds = float(refresh_before_raw)
        except ValueError as exc:
            raise ValueError("FEISHU_USER_TOKEN_REFRESH_BEFORE_SECONDS must be a number") from exc

    timeout_seconds = _resolve_timeout_seconds(args)

    if auth_mode not in {"tenant", "user", "auto"}:
        raise ConfigurationError(
            "invalid auth mode: FEISHU_AUTH_MODE/--auth-mode must be 'tenant', 'user', or 'auto'"
        )

    group = getattr(args, "group", None)
    auth_command = str(getattr(args, "auth_command", ""))
    oauth_command = str(getattr(args, "oauth_command", ""))

    skip_tenant_token_requirement = (
        (group == "oauth" and oauth_command in {"authorize-url", "exchange-code", "refresh-token"})
        or (group == "auth" and auth_command in {"login", "refresh"})
    )
    skip_user_access_token_requirement = (
        (group == "oauth" and oauth_command in {"authorize-url", "exchange-code", "refresh-token"})
        or (group == "auth" and auth_command in {"login", "refresh"})
    )

    if group == "auth":
        if auth_command == "login":
            if not app_id:
                raise ConfigurationError("auth login requires app_id")
            if not (app_access_token or (app_id and app_secret)):
                raise ConfigurationError("auth login requires app_access_token or app_id/app_secret")
        elif auth_command == "refresh":
            refresh_token_arg = getattr(args, "refresh_token", None)
            if not refresh_token_arg and not user_refresh_token:
                raise ConfigurationError("auth refresh requires --refresh-token or stored/user refresh token")
            if not (app_access_token or (app_id and app_secret)):
                raise ConfigurationError("auth refresh requires app_access_token or app_id/app_secret")
        elif auth_command == "whoami":
            if not resolved_access_token and not user_access_token and not user_refresh_token:
                raise ConfigurationError(
                    "auth whoami requires user_access_token/access_token or user_refresh_token"
                )
            if user_refresh_token and not (app_access_token or (app_id and app_secret)):
                raise ConfigurationError(
                    "refreshing user token requires app_access_token or app_id/app_secret"
                )

    if getattr(args, "group", None) == "oauth":
        if oauth_command == "authorize-url":
            if not app_id:
                raise ConfigurationError("oauth authorize-url requires app_id")
        elif oauth_command in {"exchange-code", "refresh-token"}:
            if not (app_access_token or (app_id and app_secret)):
                raise ConfigurationError("oauth token exchange requires app_access_token or app_id/app_secret")
        elif oauth_command == "user-info":
            if not resolved_access_token and not user_access_token and not user_refresh_token:
                raise ConfigurationError(
                    "oauth user-info requires user_access_token/access_token or user_refresh_token"
                )
            if user_refresh_token and not (app_access_token or (app_id and app_secret)):
                raise ConfigurationError(
                    "refreshing user token requires app_access_token or app_id/app_secret"
                )
        return FeishuConfig(
            app_id=app_id,
            app_secret=app_secret,
            auth_mode=auth_mode,
            access_token=resolved_access_token,
            app_access_token=app_access_token,
            user_access_token=user_access_token,
            user_refresh_token=user_refresh_token,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            user_access_token_expires_at=user_access_token_expires_at,
            user_refresh_token_expires_at=user_refresh_token_expires_at,
            user_token_refresh_before_seconds=refresh_before_seconds,
        )

    if auth_mode == "tenant":
        if not skip_tenant_token_requirement and not resolved_access_token and (not app_id or not app_secret):
            raise ConfigurationError(
                "tenant mode requires either access_token or app_id/app_secret"
            )
    elif auth_mode == "user":
        effective_user_access = resolved_access_token or user_access_token
        if not skip_user_access_token_requirement and not effective_user_access and not user_refresh_token:
            raise ConfigurationError(
                "user mode requires user_access_token/access_token or user_refresh_token"
            )
        if user_refresh_token and not (app_access_token or (app_id and app_secret)):
            raise ConfigurationError(
                "refreshing user token requires app_access_token or app_id/app_secret"
            )
    else:
        tenant_ready = bool(resolved_access_token or (app_id and app_secret))
        user_ready = bool(user_access_token or user_refresh_token)
        if (
            not skip_tenant_token_requirement
            and not skip_user_access_token_requirement
            and not (tenant_ready or user_ready)
        ):
            raise ConfigurationError("auto mode requires tenant credentials or user token")
        if user_refresh_token and not (app_access_token or (app_id and app_secret)):
            raise ConfigurationError(
                "refreshing user token requires app_access_token or app_id/app_secret"
            )

    return FeishuConfig(
        app_id=app_id,
        app_secret=app_secret,
        auth_mode=auth_mode,
        access_token=resolved_access_token,
        app_access_token=app_access_token,
        user_access_token=user_access_token,
        user_refresh_token=user_refresh_token,
        user_access_token_expires_at=user_access_token_expires_at,
        user_refresh_token_expires_at=user_refresh_token_expires_at,
        user_token_refresh_before_seconds=refresh_before_seconds,
        base_url=base_url,
        timeout_seconds=timeout_seconds,
    )


def _resolve_user_token_store_context(args: argparse.Namespace) -> _UserTokenStoreContext:
    profile = (
        str(getattr(args, "profile", "")).strip()
        or str(os.getenv("FEISHU_PROFILE", "")).strip()
        or "default"
    )
    no_store_raw = bool(getattr(args, "no_store", False)) or _is_truthy(os.getenv("FEISHU_NO_STORE"))
    token_store_path_value = (
        getattr(args, "token_store", None)
        or os.getenv("FEISHU_TOKEN_STORE_PATH")
        or os.getenv("FEISHU_TOKEN_STORE")
    )
    store_path = (
        Path(str(token_store_path_value))
        if token_store_path_value
        else default_token_store_path()
    )
    from_env_or_arg = any(
        bool(value)
        for value in (
            os.getenv("FEISHU_USER_ACCESS_TOKEN"),
            os.getenv("FEISHU_USER_REFRESH_TOKEN"),
            getattr(args, "user_access_token", None),
            getattr(args, "user_refresh_token", None),
        )
    )
    if no_store_raw:
        return _UserTokenStoreContext(
            enabled=False,
            profile=profile,
            store_path=store_path,
            store=None,
            from_env_or_arg=from_env_or_arg,
            loaded_token=None,
        )
    store = TokenStore(store_path)
    loaded = store.load_profile(profile)
    return _UserTokenStoreContext(
        enabled=True,
        profile=profile,
        store_path=store_path,
        store=store,
        from_env_or_arg=from_env_or_arg,
        loaded_token=loaded,
    )


def _store_user_token(args: argparse.Namespace, token: Any) -> Mapping[str, Any]:
    context = _resolve_user_token_store_context(args)
    if not context.enabled or context.store is None:
        return {
            "stored": False,
            "profile": context.profile,
            "store_path": str(context.store_path),
        }
    app_id = (
        os.getenv("FEISHU_APP_ID")
        or os.getenv("APP_ID")
        or getattr(args, "app_id", None)
    )
    context.store.save_profile(
        context.profile,
        _to_stored_user_token(token, app_id=str(app_id) if app_id else None),
    )
    return {
        "stored": True,
        "profile": context.profile,
        "store_path": str(context.store_path),
    }


def _to_stored_user_token(token: Any, *, app_id: str | None) -> StoredUserToken:
    raw_payload: Mapping[str, Any] = {}
    raw = getattr(token, "raw", None)
    if isinstance(raw, Mapping):
        raw_payload = raw
    now = time.time()
    expires_in = _to_optional_int(getattr(token, "expires_in", None))
    refresh_expires_in = _to_optional_int(getattr(token, "refresh_expires_in", None))
    expires_at = now + max(expires_in, 1) if expires_in is not None else None
    refresh_expires_at = (
        now + max(refresh_expires_in, 1)
        if refresh_expires_in is not None
        else None
    )
    scope = _to_optional_str(getattr(token, "scope", None))
    if scope is None:
        scope = _to_optional_str(raw_payload.get("scope"))
    return StoredUserToken(
        access_token=str(getattr(token, "access_token")),
        refresh_token=_to_optional_str(getattr(token, "refresh_token", None)),
        expires_at=expires_at,
        refresh_expires_at=refresh_expires_at,
        token_type=_to_optional_str(getattr(token, "token_type", None)),
        scope=scope,
        app_id=app_id,
        tenant_key=_to_optional_str(getattr(token, "tenant_key", None)),
        open_id=_to_optional_str(getattr(token, "open_id", None)),
        user_id=_to_optional_str(getattr(token, "user_id", None)),
        union_id=_to_optional_str(getattr(token, "union_id", None)),
        updated_at=now,
    )


def _resolve_oauth_redirect_uri(args: argparse.Namespace) -> str:
    redirect_uri = getattr(args, "redirect_uri", None)
    if redirect_uri:
        return str(redirect_uri)
    host = str(getattr(args, "redirect_host", _DEFAULT_OAUTH_CALLBACK_HOST))
    port = int(getattr(args, "redirect_port", _DEFAULT_OAUTH_CALLBACK_PORT))
    path = str(getattr(args, "redirect_path", _DEFAULT_OAUTH_CALLBACK_PATH))
    if not path.startswith("/"):
        path = f"/{path}"
    return f"http://{host}:{port}{path}"


def _parse_local_redirect(redirect_uri: str) -> Mapping[str, Any] | None:
    parsed = urlparse(redirect_uri)
    host = parsed.hostname
    if host not in {"127.0.0.1", "localhost"}:
        return None
    path = parsed.path or "/"
    port = parsed.port
    if port is None:
        port = 80 if parsed.scheme == "http" else 443
    return {"host": host, "port": int(port), "path": path}


def _wait_for_oauth_callback(
    *,
    host: str,
    port: int,
    path: str,
    timeout_seconds: float,
) -> Mapping[str, str]:
    result: dict[str, str] = {}
    done = threading.Event()

    class _OAuthCallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path != path:
                self.send_response(404)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"Not Found")
                return
            query = parse_qs(parsed.query, keep_blank_values=True)
            error = _first_query(query, "error")
            if error:
                result["error"] = error
                result["error_description"] = _first_query(query, "error_description") or ""
                done.set()
                self.send_response(400)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"OAuth authorization failed.")
                return
            code = _first_query(query, "code")
            state = _first_query(query, "state")
            if not code:
                self.send_response(400)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"Missing code.")
                return
            result["code"] = code
            if state:
                result["state"] = state
            done.set()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h3>Feishu authorization completed.</h3>"
                b"<p>You can close this tab now.</p></body></html>"
            )

        def log_message(self, format: str, *args: Any) -> None:
            return

    server = ThreadingHTTPServer((host, port), _OAuthCallbackHandler)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True)
    thread.start()
    try:
        if not done.wait(timeout=timeout_seconds):
            raise TimeoutError(
                f"oauth callback timeout after {timeout_seconds:.0f}s, "
                "please check redirect URI and app security settings"
            )
        error = result.get("error")
        if error:
            error_description = result.get("error_description")
            if error_description:
                raise ValueError(f"oauth authorization failed: {error} ({error_description})")
            raise ValueError(f"oauth authorization failed: {error}")
        code = result.get("code")
        if not code:
            raise ValueError("oauth callback missing authorization code")
        payload: dict[str, str] = {"code": code}
        state = result.get("state")
        if state:
            payload["state"] = state
        return payload
    finally:
        with contextlib.suppress(Exception):
            server.shutdown()
        with contextlib.suppress(Exception):
            server.server_close()
        thread.join(timeout=1.0)


def _generate_state() -> str:
    return secrets.token_urlsafe(24)


def _generate_pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def _first_query(query: Mapping[str, list[str]], key: str) -> str | None:
    values = query.get(key)
    if not values:
        return None
    value = values[0]
    return value if value else None


def _is_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _to_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _to_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return int(text)
        except ValueError:
            return None
    return None


def _resolve_timeout_seconds(args: argparse.Namespace) -> float:
    env_timeout = os.getenv("FEISHU_TIMEOUT_SECONDS")
    timeout = getattr(args, "timeout", None)
    if timeout is None and env_timeout:
        try:
            timeout = float(env_timeout)
        except ValueError as exc:
            raise ValueError("FEISHU_TIMEOUT_SECONDS must be a number") from exc
    return float(timeout) if timeout is not None else _DEFAULT_TIMEOUT_SECONDS


def _resolve_app_credentials(args: argparse.Namespace) -> tuple[str, str]:
    app_id = os.getenv("FEISHU_APP_ID") or os.getenv("APP_ID") or getattr(args, "app_id", None)
    app_secret = os.getenv("FEISHU_APP_SECRET") or os.getenv("APP_SECRET") or getattr(args, "app_secret", None)
    if not app_id or not app_secret:
        raise ConfigurationError(
            "missing app credentials: set FEISHU_APP_ID/FEISHU_APP_SECRET env vars, "
            "or pass --app-id and --app-secret"
        )
    return str(app_id), str(app_secret)


def _resolve_open_domain(args: argparse.Namespace) -> str:
    return (
        getattr(args, "domain", None)
        or os.getenv("FEISHU_WS_DOMAIN")
        or os.getenv("FEISHU_OPEN_DOMAIN")
        or "https://open.feishu.cn"
    )


def _resolve_encrypt_key(args: argparse.Namespace, *, required: bool) -> str | None:
    encrypt_key = (
        getattr(args, "encrypt_key", None)
        or os.getenv("FEISHU_ENCRYPT_KEY")
        or os.getenv("FEISHU_EVENT_ENCRYPT_KEY")
    )
    if required and not encrypt_key:
        raise ConfigurationError("missing encrypt key: set FEISHU_ENCRYPT_KEY or pass --encrypt-key")
    if encrypt_key is None:
        return None
    return str(encrypt_key)


__all__ = [name for name in globals() if not name.startswith("__")]
