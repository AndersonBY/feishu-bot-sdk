from __future__ import annotations

import argparse

from ..settings import (
    DEFAULT_BASE_URL as _DEFAULT_BASE_URL,
    DEFAULT_TIMEOUT_SECONDS as _DEFAULT_TIMEOUT_SECONDS,
)

def _add_global_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=("human", "json"),
        default="human",
        help="Output format. Default: human",
    )
    parser.add_argument("--app-id", help="Feishu app_id")
    parser.add_argument("--app-secret", help="Feishu app_secret")
    parser.add_argument(
        "--auth-mode",
        choices=("tenant", "user"),
        help="Auth mode for API calls. Default: tenant",
    )
    parser.add_argument("--access-token", help="Static access token for selected auth mode")
    parser.add_argument("--app-access-token", help="Static app_access_token for OAuth token exchange")
    parser.add_argument("--user-access-token", help="Static user_access_token")
    parser.add_argument("--user-refresh-token", help="User refresh_token for auto refresh")
    parser.add_argument("--profile", help="Token profile name. Default: FEISHU_PROFILE or default")
    parser.add_argument("--token-store", help="Token store file path")
    parser.add_argument("--no-store", action="store_true", help="Disable reading/writing local token store")
    parser.add_argument("--base-url", help=f"Feishu OpenAPI base url. Default: {_DEFAULT_BASE_URL}")
    parser.add_argument("--timeout", type=float, help=f"HTTP timeout seconds. Default: {_DEFAULT_TIMEOUT_SECONDS}")

def _add_receive_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--receive-id", required=True, help="receive_id")
    parser.add_argument(
        "--receive-id-type",
        default="open_id",
        choices=("open_id", "user_id", "union_id", "email", "chat_id"),
        help="open_id/user_id/union_id/email/chat_id (default: open_id)",
    )

def _add_webhook_body_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--body-json", help="Raw webhook body JSON string")
    parser.add_argument("--body-file", help="Raw webhook body file path")
    parser.add_argument("--body-stdin", action="store_true", help="Read raw webhook body JSON from stdin")
