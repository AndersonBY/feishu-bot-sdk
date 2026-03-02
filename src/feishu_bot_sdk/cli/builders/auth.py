from __future__ import annotations

import argparse

from ..commands import (
    _cmd_auth_login,
    _cmd_auth_logout,
    _cmd_auth_refresh,
    _cmd_auth_request,
    _cmd_auth_token,
    _cmd_auth_whoami,
    _cmd_bot_info,
    _cmd_oauth_authorize_url,
    _cmd_oauth_exchange_code,
    _cmd_oauth_refresh_token,
    _cmd_oauth_user_info,
)
from ..settings import (
    AUTH_HELP_EPILOG as _AUTH_HELP_EPILOG,
    DEFAULT_OAUTH_CALLBACK_HOST as _DEFAULT_OAUTH_CALLBACK_HOST,
    DEFAULT_OAUTH_CALLBACK_PATH as _DEFAULT_OAUTH_CALLBACK_PATH,
    DEFAULT_OAUTH_CALLBACK_PORT as _DEFAULT_OAUTH_CALLBACK_PORT,
    HELP_FORMATTER as _HELP_FORMATTER,
)

def _build_auth_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    shared: argparse.ArgumentParser,
) -> None:
    auth_parser = subparsers.add_parser(
        "auth",
        help="Authentication and raw API request",
        description=(
            "Authentication and token lifecycle operations.\n"
            "Use `auth login` for User Auth (OAuth with localhost callback),\n"
            "then use `auth whoami` to verify token usability."
        ),
        formatter_class=_HELP_FORMATTER,
        epilog=_AUTH_HELP_EPILOG,
    )
    auth_sub = auth_parser.add_subparsers(dest="auth_command")
    auth_sub.required = True

    token_parser = auth_sub.add_parser("token", help="Get access token for current auth mode", parents=[shared])
    token_parser.set_defaults(handler=_cmd_auth_token)

    login_parser = auth_sub.add_parser(
        "login",
        help="Interactive OAuth login for user_access_token",
        parents=[shared],
        description=(
            "Run OAuth authorization code flow and persist user tokens.\n"
            "Default callback: http://127.0.0.1:18080/callback\n"
            "The exact redirect URI must be pre-configured in Feishu console."
        ),
        formatter_class=_HELP_FORMATTER,
        epilog=(
            "Examples:\n"
            "  feishu auth login --scope \"offline_access contact:user:search\" --no-browser --format json\n"
            "  feishu auth login --redirect-uri http://127.0.0.1:8080/callback --format json\n"
            "\n"
            "Notes:\n"
            "  - If --no-browser is set, CLI prints Authorize URL to stderr.\n"
            "  - Token precedence remains: env > flags > local store."
        ),
    )
    login_parser.add_argument("--scope", help="OAuth scope string")
    login_parser.add_argument("--state", help="OAuth state. Auto-generated when omitted")
    login_parser.add_argument("--redirect-uri", help="OAuth redirect URI. Default: local callback URI")
    login_parser.add_argument("--redirect-host", default=_DEFAULT_OAUTH_CALLBACK_HOST, help="Local callback host")
    login_parser.add_argument("--redirect-port", type=int, default=_DEFAULT_OAUTH_CALLBACK_PORT, help="Local callback port")
    login_parser.add_argument("--redirect-path", default=_DEFAULT_OAUTH_CALLBACK_PATH, help="Local callback path")
    login_parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=180.0,
        help="Timeout waiting for callback",
    )
    login_parser.add_argument("--no-browser", action="store_true", help="Do not auto-open browser")
    login_parser.add_argument("--no-pkce", action="store_true", help="Disable PKCE")
    login_parser.set_defaults(handler=_cmd_auth_login)

    refresh_parser = auth_sub.add_parser(
        "refresh",
        help="Refresh user access token",
        parents=[shared],
        description=(
            "Refresh user_access_token using refresh_token.\n"
            "By default reads refresh_token from env/flags/local token store."
        ),
        formatter_class=_HELP_FORMATTER,
    )
    refresh_parser.add_argument("--refresh-token", help="OAuth refresh token")
    refresh_parser.set_defaults(handler=_cmd_auth_refresh)

    whoami_parser = auth_sub.add_parser(
        "whoami",
        help="Get current user info via user token",
        parents=[shared],
        description=(
            "Validate current user token by calling /authen/v1/user_info.\n"
            "Auto refresh is attempted when token is near expiry or invalid."
        ),
        formatter_class=_HELP_FORMATTER,
    )
    whoami_parser.set_defaults(handler=_cmd_auth_whoami)

    logout_parser = auth_sub.add_parser("logout", help="Clear local stored user tokens", parents=[shared])
    logout_parser.add_argument("--all-profiles", action="store_true", help="Remove all profiles in token store")
    logout_parser.set_defaults(handler=_cmd_auth_logout)

    request_parser = auth_sub.add_parser("request", help="Send a raw Feishu OpenAPI request", parents=[shared])
    request_parser.add_argument("method", help="HTTP method, e.g. GET/POST/PUT/PATCH/DELETE")
    request_parser.add_argument("path", help="API path under /open-apis, e.g. /im/v1/messages")
    request_parser.add_argument("--params-json", help="Query params as JSON object string")
    request_parser.add_argument("--params-file", help="Query params JSON file path")
    request_parser.add_argument("--params-stdin", action="store_true", help="Read query params JSON from stdin")
    request_parser.add_argument("--payload-json", help="Request body as JSON object string")
    request_parser.add_argument("--payload-file", help="Request body JSON file path")
    request_parser.add_argument("--payload-stdin", action="store_true", help="Read request body JSON from stdin")
    request_parser.set_defaults(handler=_cmd_auth_request)

def _build_oauth_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    shared: argparse.ArgumentParser,
) -> None:
    oauth_parser = subparsers.add_parser("oauth", help="OAuth user token operations")
    oauth_sub = oauth_parser.add_subparsers(dest="oauth_command")
    oauth_sub.required = True

    authorize_url = oauth_sub.add_parser("authorize-url", help="Build OAuth authorize URL", parents=[shared])
    authorize_url.add_argument("--redirect-uri", required=True, help="OAuth redirect URI")
    authorize_url.add_argument("--scope", help="OAuth scope string")
    authorize_url.add_argument("--state", help="OAuth state value")
    authorize_url.set_defaults(handler=_cmd_oauth_authorize_url)

    exchange_code = oauth_sub.add_parser("exchange-code", help="Exchange authorization code", parents=[shared])
    exchange_code.add_argument("--code", required=True, help="OAuth authorization code")
    exchange_code.add_argument("--grant-type", default="authorization_code", help="Grant type")
    exchange_code.add_argument("--redirect-uri", help="OAuth redirect_uri used in authorize step")
    exchange_code.add_argument("--code-verifier", help="PKCE code_verifier")
    exchange_code.set_defaults(handler=_cmd_oauth_exchange_code)

    refresh_token = oauth_sub.add_parser("refresh-token", help="Refresh user access token", parents=[shared])
    refresh_token.add_argument("--refresh-token", help="OAuth refresh token")
    refresh_token.set_defaults(handler=_cmd_oauth_refresh_token)

    user_info = oauth_sub.add_parser("user-info", help="Get user profile via user_access_token", parents=[shared])
    user_info.set_defaults(handler=_cmd_oauth_user_info)

def _build_bot_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    shared: argparse.ArgumentParser,
) -> None:
    bot_parser = subparsers.add_parser("bot", help="Bot profile operations")
    bot_sub = bot_parser.add_subparsers(dest="bot_command")
    bot_sub.required = True

    info = bot_sub.add_parser("info", help="Get bot profile", parents=[shared])
    info.set_defaults(handler=_cmd_bot_info)
