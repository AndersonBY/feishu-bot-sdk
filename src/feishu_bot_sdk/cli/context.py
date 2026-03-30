from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any, Callable

import click

from .runtime.output import _print_result


RUNTIME_OPTION_NAMES = (
    "access_token",
    "app_access_token",
    "app_id",
    "app_secret",
    "as_type",
    "base_url",
    "full_output",
    "max_output_chars",
    "no_store",
    "output_format",
    "output_offset",
    "profile",
    "save_output",
    "timeout",
    "token_store",
    "user_access_token",
    "user_refresh_token",
)


@dataclass(frozen=True)
class CLIContext:
    output_format: str = "json"
    max_output_chars: int | None = 25000
    output_offset: int | None = 0
    full_output: bool = False
    save_output: str | None = None
    app_id: str | None = None
    app_secret: str | None = None
    access_token: str | None = None
    app_access_token: str | None = None
    user_access_token: str | None = None
    user_refresh_token: str | None = None
    profile: str | None = None
    token_store: str | None = None
    no_store: bool = False
    base_url: str | None = None
    timeout: float | None = None
    as_type: str = "auto"

    def normalized_output_format(self) -> str:
        if self.output_format == "human":
            return "pretty"
        return self.output_format

    def build_args(self, **overrides: Any) -> argparse.Namespace:
        auth_mode = overrides.pop("auth_mode", None)
        if auth_mode is None:
            auth_mode = identity_to_auth_mode(self.as_type)
        payload: dict[str, Any] = {
            "output_format": self.normalized_output_format(),
            "max_output_chars": self.max_output_chars,
            "output_offset": self.output_offset,
            "full_output": self.full_output,
            "save_output": self.save_output,
            "app_id": self.app_id,
            "app_secret": self.app_secret,
            "access_token": self.access_token,
            "app_access_token": self.app_access_token,
            "user_access_token": self.user_access_token,
            "user_refresh_token": self.user_refresh_token,
            "profile": self.profile,
            "token_store": self.token_store,
            "no_store": self.no_store,
            "base_url": self.base_url,
            "timeout": self.timeout,
            "auth_mode": auth_mode,
        }
        payload.update(overrides)
        return argparse.Namespace(**payload)

    def emit(self, result: Any, *, cli_args: argparse.Namespace | None = None) -> None:
        _print_result(
            result,
            output_format=self.normalized_output_format(),
            max_output_chars=self.max_output_chars,
            output_offset=self.output_offset,
            full_output=self.full_output,
            save_output=self.save_output,
            cli_args=cli_args,
        )


def identity_to_auth_mode(identity: str) -> str:
    normalized = str(identity or "auto").strip().lower() or "auto"
    if normalized == "bot":
        return "tenant"
    return normalized


def build_cli_context(values: dict[str, Any]) -> tuple[CLIContext, dict[str, Any]]:
    remaining = dict(values)
    payload = {name: remaining.pop(name) for name in RUNTIME_OPTION_NAMES if name in remaining}
    return CLIContext(**payload), remaining


def with_runtime_options(
    func: Callable[..., Any] | None = None,
    *,
    include_identity: bool = True,
) -> Callable[..., Any]:
    options = [
        click.option("--timeout", type=float, help="HTTP timeout seconds"),
        click.option("--base-url", help="Feishu OpenAPI base URL"),
        click.option("--no-store", is_flag=True, help="Disable reading/writing local token store"),
        click.option("--token-store", help="Token store file path"),
        click.option("--profile", help="CLI profile name"),
        click.option("--user-refresh-token", help="Static user refresh_token"),
        click.option("--user-access-token", help="Static user access_token"),
        click.option("--app-access-token", help="Static app_access_token"),
        click.option("--access-token", help="Static access token for the selected identity"),
        click.option("--app-secret", help="Feishu app_secret"),
        click.option("--app-id", help="Feishu app_id"),
        click.option("--save-output", help="Write the full normalized JSON result to a file before stdout truncation"),
        click.option("--full-output", is_flag=True, help="Disable stdout truncation for regular command results"),
        click.option("--output-offset", type=int, default=0, show_default=True, help="Start JSON preview from this character offset"),
        click.option("--max-output-chars", type=int, default=25000, show_default=True, help="Maximum stdout characters for regular command results"),
        click.option(
            "--format",
            "output_format",
            type=click.Choice(["json", "pretty", "table", "csv", "ndjson", "human"]),
            default="json",
            show_default=True,
            help="Output format",
        ),
    ]
    if include_identity:
        options.insert(
            0,
            click.option(
                "--as",
                "as_type",
                type=click.Choice(["user", "bot", "auto"]),
                default="auto",
                show_default=True,
                help="Identity type: user | bot | auto",
            ),
        )

    def decorator(callback: Callable[..., Any]) -> Callable[..., Any]:
        wrapped = callback
        for option in reversed(options):
            wrapped = option(wrapped)
        return wrapped

    if func is None:
        return decorator
    return decorator(func)


def with_service_io_options(func: Callable[..., Any]) -> Callable[..., Any]:
    options = [
        click.option("--dry-run", is_flag=True, help="Print request plan without executing"),
        click.option("--output", help="Write command semantic output to a file"),
        click.option("--page-delay", type=int, default=200, show_default=True, help="Delay in ms between pages"),
        click.option("--page-limit", type=int, default=10, show_default=True, help="Max pages to fetch when --page-all is enabled (0 = unlimited)"),
        click.option("--page-size", type=int, help="Page size override"),
        click.option("--page-all", is_flag=True, help="Automatically fetch paginated results"),
        click.option("--data", help="Request body JSON"),
        click.option("--params", help="URL/query parameters JSON"),
    ]
    wrapped = func
    for option in reversed(options):
        wrapped = option(wrapped)
    return wrapped
