from __future__ import annotations

import argparse
from typing import Sequence

from ..exceptions import ConfigurationError, FeishuError, HTTPRequestError
from ..server import FeishuBotServer
from ..ws import AsyncLongConnectionClient, fetch_ws_endpoint
from .builders import (
    _add_global_args,
    _build_auth_commands,
    _build_bitable_commands,
    _build_bot_commands,
    _build_calendar_commands,
    _build_chat_commands,
    _build_contact_commands,
    _build_docx_commands,
    _build_drive_commands,
    _build_im_commands,
    _build_mail_commands,
    _build_media_commands,
    _build_oauth_commands,
    _build_search_commands,
    _build_server_commands,
    _build_sheets_commands,
    _build_task_commands,
    _build_webhook_commands,
    _build_wiki_commands,
    _build_ws_commands,
)
from .runtime import (
    _UserTokenStoreContext,
    _build_client,
    _build_config,
    _extract_required_tenant_scopes,
    _format_configuration_error_message,
    _extract_required_user_scopes,
    _format_feishu_error_message,
    _format_http_error,
    _is_process_alive,
    _print_error,
    _print_result,
    _serve_webhook_http,
    _spawn_background_process,
    _system_exit_code,
    _terminate_process,
    _to_jsonable,
    _wait_for_oauth_callback,
)
from .settings import HELP_FORMATTER, ROOT_HELP_EPILOG


def build_parser() -> argparse.ArgumentParser:
    shared = argparse.ArgumentParser(add_help=False)
    _add_global_args(shared)

    parser = argparse.ArgumentParser(
        prog="feishu",
        description="Feishu CLI powered by feishu-bot-sdk",
        parents=[shared],
        formatter_class=HELP_FORMATTER,
        epilog=ROOT_HELP_EPILOG,
    )
    subparsers = parser.add_subparsers(dest="group")
    subparsers.required = True

    _build_auth_commands(subparsers, shared)
    _build_oauth_commands(subparsers, shared)
    _build_bot_commands(subparsers, shared)
    _build_chat_commands(subparsers, shared)
    _build_im_commands(subparsers, shared)
    _build_media_commands(subparsers, shared)
    _build_bitable_commands(subparsers, shared)
    _build_docx_commands(subparsers, shared)
    _build_drive_commands(subparsers, shared)
    _build_wiki_commands(subparsers, shared)
    _build_mail_commands(subparsers, shared)
    _build_calendar_commands(subparsers, shared)
    _build_contact_commands(subparsers, shared)
    _build_search_commands(subparsers, shared)
    _build_sheets_commands(subparsers, shared)
    _build_task_commands(subparsers, shared)
    _build_webhook_commands(subparsers, shared)
    _build_ws_commands(subparsers, shared)
    _build_server_commands(subparsers, shared)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    output_format = "human"
    try:
        args = parser.parse_args(argv)
        output_format = str(args.output_format)
        handler = getattr(args, "handler", None)
        if handler is None:
            raise ValueError("missing command handler")
        result = handler(args)
        _print_result(
            result,
            output_format=output_format,
            max_output_chars=getattr(args, "max_output_chars", None),
            output_offset=getattr(args, "output_offset", None),
            full_output=bool(getattr(args, "full_output", False)),
            save_output=getattr(args, "save_output", None),
            cli_args=args,
        )
        return 0
    except SystemExit as exc:
        return _system_exit_code(exc)
    except ConfigurationError as exc:
        message = _format_configuration_error_message(str(exc))
        return _print_error(message, exit_code=2, output_format=output_format)
    except ValueError as exc:
        return _print_error(str(exc), exit_code=2, output_format=output_format)
    except HTTPRequestError as exc:
        message = _format_http_error(exc)
        return _print_error(message, exit_code=4, output_format=output_format)
    except FeishuError as exc:
        message = _format_feishu_error_message(str(exc))
        return _print_error(message, exit_code=3, output_format=output_format)
    except Exception as exc:
        return _print_error(f"{type(exc).__name__}: {exc}", exit_code=1, output_format=output_format)


__all__ = [
    "main",
    "build_parser",
    "FeishuBotServer",
    "AsyncLongConnectionClient",
    "fetch_ws_endpoint",
    "_UserTokenStoreContext",
    "_build_client",
    "_build_config",
    "_extract_required_tenant_scopes",
    "_format_configuration_error_message",
    "_extract_required_user_scopes",
    "_format_feishu_error_message",
    "_wait_for_oauth_callback",
    "_serve_webhook_http",
    "_spawn_background_process",
    "_is_process_alive",
    "_terminate_process",
    "_format_http_error",
    "_print_error",
    "_print_result",
    "_system_exit_code",
    "_to_jsonable",
]
