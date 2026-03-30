from __future__ import annotations

from importlib import metadata
import sys
from typing import Sequence

import click

from ..exceptions import ConfigurationError, FeishuError, HTTPRequestError
from .groups import (
    api_command,
    auth_group,
    completion_command,
    config_group,
    doctor_command,
    docx_group,
    media_group,
    register_service_groups,
    schema_group,
    server_group,
    webhook_group,
    ws_group,
)
from .runtime import (
    _build_configuration_error_detail,
    _build_feishu_error_detail,
    _build_http_error_detail,
    _print_error,
)
from .shortcuts import attach_shortcuts


def _version() -> str:
    try:
        return metadata.version("feishu-bot-sdk")
    except metadata.PackageNotFoundError:
        return "0.0.0"


@click.group(
    context_settings={"help_option_names": ["-h", "--help"]},
    invoke_without_command=False,
)
@click.version_option(version=_version(), prog_name="feishu")
def app() -> None:
    """Feishu CLI aligned to the lark-cli command model."""


def _register_static_groups() -> None:
    app.add_command(config_group)
    app.add_command(auth_group)
    app.add_command(api_command)
    app.add_command(schema_group)
    app.add_command(doctor_command)
    app.add_command(completion_command)
    app.add_command(docx_group)
    app.add_command(webhook_group)
    app.add_command(ws_group)
    app.add_command(server_group)
    app.add_command(media_group)
    for shortcut_only_service in ("bitable",):
        group = click.Group(shortcut_only_service, help=f"{shortcut_only_service} shortcuts")
        attach_shortcuts(group, shortcut_only_service)
        app.add_command(group)
    register_service_groups(app)


_register_static_groups()


def main(argv: Sequence[str] | None = None) -> int:
    effective_argv = list(argv) if argv is not None else sys.argv[1:]
    output_format = _sniff_output_format(effective_argv)
    try:
        app.main(args=effective_argv, prog_name="feishu", standalone_mode=False)
        return 0
    except click.exceptions.Exit as exc:
        return int(exc.exit_code)
    except click.ClickException as exc:
        return _print_error(str(exc), exit_code=2, output_format=output_format, error_type="usage_error")
    except ConfigurationError as exc:
        return _print_error(
            _build_configuration_error_detail(str(exc)),
            exit_code=2,
            output_format=output_format,
        )
    except HTTPRequestError as exc:
        return _print_error(_build_http_error_detail(exc), exit_code=4, output_format=output_format)
    except FeishuError as exc:
        return _print_error(_build_feishu_error_detail(str(exc)), exit_code=3, output_format=output_format)
    except ValueError as exc:
        return _print_error(str(exc), exit_code=2, output_format=output_format, error_type="validation_error")
    except Exception as exc:
        return _print_error(
            f"{type(exc).__name__}: {exc}",
            exit_code=1,
            output_format=output_format,
            error_type="internal_error",
        )


def _sniff_output_format(argv: Sequence[str] | None) -> str:
    values = list(argv or [])
    for index, item in enumerate(values):
        if item == "--format" and index + 1 < len(values):
            return _normalize_output_format(values[index + 1])
        if item.startswith("--format="):
            return _normalize_output_format(item.split("=", 1)[1])
    return "json"


def _normalize_output_format(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized == "human":
        return "pretty"
    return normalized or "json"


__all__ = ["app", "main"]
