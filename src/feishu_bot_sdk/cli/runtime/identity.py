from __future__ import annotations

from dataclasses import dataclass
import os

from ..context import CLIContext
from .auth import _resolve_user_token_store_context
from .profiles import resolve_cli_profile
from .secret_store import resolve_secret_store


@dataclass(frozen=True)
class IdentityResolution:
    identity: str
    supported: tuple[str, ...]
    source: str
    explicit: bool
    user_available: bool
    bot_available: bool


def identity_to_auth_mode(identity: str) -> str:
    normalized = normalize_identity(identity)
    if normalized == "bot":
        return "tenant"
    return normalized


def normalize_identity(value: str | None) -> str:
    normalized = str(value or "auto").strip().lower() or "auto"
    if normalized not in {"user", "bot", "auto"}:
        raise ValueError("identity must be one of: user, bot, auto")
    return normalized


def available_identities(cli_ctx: CLIContext) -> tuple[bool, bool]:
    user_available = _user_identity_available(cli_ctx)
    bot_available = _bot_identity_available(cli_ctx)
    return user_available, bot_available


def resolve_identity(cli_ctx: CLIContext, supported: tuple[str, ...] | list[str] | None = None) -> IdentityResolution:
    supported_identities = tuple(normalize_identity(item) for item in (supported or ("user", "bot")) if item != "auto")
    explicit_identity = normalize_identity(cli_ctx.as_type)
    user_available, bot_available = available_identities(cli_ctx)

    if explicit_identity != "auto":
        if supported_identities and explicit_identity not in supported_identities:
            raise _unsupported_identity_error(explicit_identity, supported_identities, explicit=True)
        return IdentityResolution(
            identity=explicit_identity,
            supported=supported_identities,
            source="flag",
            explicit=True,
            user_available=user_available,
            bot_available=bot_available,
        )

    if len(supported_identities) == 1:
        chosen = supported_identities[0]
        if chosen == "user" and not user_available and bot_available:
            raise _unsupported_identity_error("user", supported_identities, explicit=False)
        return IdentityResolution(
            identity=chosen,
            supported=supported_identities,
            source="metadata",
            explicit=False,
            user_available=user_available,
            bot_available=bot_available,
        )

    default_as = _resolve_default_as(cli_ctx)
    if default_as and default_as != "auto":
        if supported_identities and default_as not in supported_identities:
            raise _unsupported_identity_error(default_as, supported_identities, explicit=False)
        return IdentityResolution(
            identity=default_as,
            supported=supported_identities,
            source="default_as",
            explicit=False,
            user_available=user_available,
            bot_available=bot_available,
        )

    if user_available and (not supported_identities or "user" in supported_identities):
        return IdentityResolution(
            identity="user",
            supported=supported_identities,
            source="login_state",
            explicit=False,
            user_available=user_available,
            bot_available=bot_available,
        )

    if bot_available and (not supported_identities or "bot" in supported_identities):
        return IdentityResolution(
            identity="bot",
            supported=supported_identities,
            source="login_state",
            explicit=False,
            user_available=user_available,
            bot_available=bot_available,
        )

    fallback = supported_identities[0] if supported_identities else "bot"
    if supported_identities and fallback not in supported_identities:
        raise _unsupported_identity_error(fallback, supported_identities, explicit=False)
    return IdentityResolution(
        identity=fallback,
        supported=supported_identities,
        source="fallback",
        explicit=False,
        user_available=user_available,
        bot_available=bot_available,
    )


def _resolve_default_as(cli_ctx: CLIContext) -> str:
    for env_name in ("FEISHU_DEFAULT_AS", "LARKSUITE_CLI_DEFAULT_AS"):
        value = normalize_identity_or_empty(os.getenv(env_name))
        if value:
            return value
    _, profile, _ = resolve_cli_profile(cli_ctx.profile)
    if profile is None:
        return ""
    return normalize_identity_or_empty(profile.default_as)


def normalize_identity_or_empty(value: str | None) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    if not text:
        return ""
    if text not in {"user", "bot", "auto"}:
        return ""
    return text


def _user_identity_available(cli_ctx: CLIContext) -> bool:
    if cli_ctx.user_access_token or cli_ctx.user_refresh_token:
        return True
    if os.getenv("FEISHU_USER_ACCESS_TOKEN") or os.getenv("FEISHU_USER_REFRESH_TOKEN"):
        return True
    args = cli_ctx.build_args(auth_mode="user")
    if args.user_access_token or args.user_refresh_token:
        return True
    try:
        token_context = _resolve_user_token_store_context(args)
    except Exception:
        return False
    loaded = token_context.loaded_token
    return bool(loaded and (loaded.access_token or loaded.refresh_token))


def _bot_identity_available(cli_ctx: CLIContext) -> bool:
    if cli_ctx.access_token or cli_ctx.app_access_token:
        return True
    if cli_ctx.app_id and cli_ctx.app_secret:
        return True
    if os.getenv("FEISHU_ACCESS_TOKEN") or os.getenv("FEISHU_APP_ACCESS_TOKEN"):
        return True
    env_app_id = os.getenv("FEISHU_APP_ID") or os.getenv("APP_ID")
    env_app_secret = os.getenv("FEISHU_APP_SECRET") or os.getenv("APP_SECRET")
    if env_app_id and env_app_secret:
        return True
    _, profile, _ = resolve_cli_profile(cli_ctx.profile)
    if profile is None or not profile.app_id:
        return False
    if profile.app_secret_ref is not None:
        try:
            return resolve_secret_store().get(profile.app_secret_ref) is not None
        except Exception:
            return False
    return False


def _unsupported_identity_error(identity: str, supported: tuple[str, ...], *, explicit: bool) -> ValueError:
    supported_text = ", ".join(supported)
    if explicit:
        return ValueError(f"--as {identity} is not supported; this command only supports: {supported_text}")
    return ValueError(
        f"resolved identity {identity!r} is not supported; this command only supports: {supported_text}. "
        f"Hint: use --as {supported[0]}"
    )


__all__ = [
    "IdentityResolution",
    "available_identities",
    "identity_to_auth_mode",
    "normalize_identity",
    "resolve_identity",
]
