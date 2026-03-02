from __future__ import annotations

import asyncio
import argparse
import contextlib
import dataclasses
import json
import os
import signal
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from .bitable import BitableService
from .bot import BotService
from .calendar import CalendarService
from .config import FeishuConfig
from .docs_content import DocContentService
from .docx import DocxService
from .drive_files import DriveFileService
from .drive_permissions import DrivePermissionService
from .events import EventContext, FeishuEventRegistry, parse_event_envelope
from .exceptions import ConfigurationError, FeishuError, HTTPRequestError
from .feishu import FeishuClient
from .im import MediaService, MessageService
from .server import FeishuBotServer
from .webhook import (
    WebhookReceiver,
    build_challenge_response,
    decode_webhook_body,
    verify_signature,
)
from .wiki import WikiService
from .ws import AsyncLongConnectionClient, fetch_ws_endpoint

_DEFAULT_BASE_URL = "https://open.feishu.cn/open-apis"
_DEFAULT_TIMEOUT_SECONDS = 30.0


def build_parser() -> argparse.ArgumentParser:
    shared = argparse.ArgumentParser(add_help=False)
    _add_global_args(shared)

    parser = argparse.ArgumentParser(
        prog="feishu",
        description="Feishu CLI powered by feishu-bot-sdk",
        parents=[shared],
    )
    subparsers = parser.add_subparsers(dest="group")
    subparsers.required = True

    _build_auth_commands(subparsers, shared)
    _build_oauth_commands(subparsers, shared)
    _build_bot_commands(subparsers, shared)
    _build_im_commands(subparsers, shared)
    _build_media_commands(subparsers, shared)
    _build_bitable_commands(subparsers, shared)
    _build_docx_commands(subparsers, shared)
    _build_drive_commands(subparsers, shared)
    _build_wiki_commands(subparsers, shared)
    _build_calendar_commands(subparsers, shared)
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
        _print_result(result, output_format=output_format)
        return 0
    except SystemExit as exc:
        return _system_exit_code(exc)
    except ConfigurationError as exc:
        return _print_error(str(exc), exit_code=2, output_format=output_format)
    except ValueError as exc:
        return _print_error(str(exc), exit_code=2, output_format=output_format)
    except HTTPRequestError as exc:
        message = _format_http_error(exc)
        return _print_error(message, exit_code=4, output_format=output_format)
    except FeishuError as exc:
        return _print_error(str(exc), exit_code=3, output_format=output_format)
    except Exception as exc:
        return _print_error(f"{type(exc).__name__}: {exc}", exit_code=1, output_format=output_format)


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
    parser.add_argument("--base-url", help=f"Feishu OpenAPI base url. Default: {_DEFAULT_BASE_URL}")
    parser.add_argument("--timeout", type=float, help=f"HTTP timeout seconds. Default: {_DEFAULT_TIMEOUT_SECONDS}")


def _build_auth_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    shared: argparse.ArgumentParser,
) -> None:
    auth_parser = subparsers.add_parser("auth", help="Authentication and raw API request")
    auth_sub = auth_parser.add_subparsers(dest="auth_command")
    auth_sub.required = True

    token_parser = auth_sub.add_parser("token", help="Get access token for current auth mode", parents=[shared])
    token_parser.set_defaults(handler=_cmd_auth_token)

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


def _build_im_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    shared: argparse.ArgumentParser,
) -> None:
    im_parser = subparsers.add_parser("im", help="Instant messaging")
    im_sub = im_parser.add_subparsers(dest="im_command")
    im_sub.required = True

    send_text = im_sub.add_parser("send-text", help="Send text message", parents=[shared])
    _add_receive_args(send_text)
    send_text.add_argument("--text", required=True, help="Text message body")
    send_text.add_argument("--uuid", help="Client message id for idempotency")
    send_text.set_defaults(handler=_cmd_im_send_text)

    send_markdown = im_sub.add_parser("send-markdown", help="Send markdown message", parents=[shared])
    _add_receive_args(send_markdown)
    send_markdown.add_argument("--markdown", help="Markdown text")
    send_markdown.add_argument("--markdown-file", help="Markdown file path")
    send_markdown.add_argument("--markdown-stdin", action="store_true", help="Read markdown text from stdin")
    send_markdown.add_argument("--locale", default="zh_cn", help="Locale key. Default: zh_cn")
    send_markdown.add_argument("--title", help="Post title")
    send_markdown.add_argument("--uuid", help="Client message id for idempotency")
    send_markdown.set_defaults(handler=_cmd_im_send_markdown)

    reply_markdown = im_sub.add_parser(
        "reply-markdown",
        help="Reply a markdown message by message_id",
        parents=[shared],
    )
    reply_markdown.add_argument("message_id", help="Original message_id")
    reply_markdown.add_argument("--markdown", help="Markdown text")
    reply_markdown.add_argument("--markdown-file", help="Markdown file path")
    reply_markdown.add_argument("--markdown-stdin", action="store_true", help="Read markdown text from stdin")
    reply_markdown.add_argument("--locale", default="zh_cn", help="Locale key. Default: zh_cn")
    reply_markdown.add_argument("--title", help="Post title")
    reply_markdown.add_argument("--uuid", help="Client message id for idempotency")
    reply_markdown.set_defaults(handler=_cmd_im_reply_markdown)

    send = im_sub.add_parser("send", help="Send generic message by msg_type + content", parents=[shared])
    _add_receive_args(send)
    send.add_argument("--msg-type", required=True, help="Feishu msg_type")
    send.add_argument("--content-json", help="Message content JSON object string")
    send.add_argument("--content-file", help="Message content JSON file path")
    send.add_argument("--content-stdin", action="store_true", help="Read message content JSON from stdin")
    send.add_argument("--uuid", help="Client message id for idempotency")
    send.set_defaults(handler=_cmd_im_send_generic)

    reply = im_sub.add_parser("reply", help="Reply generic message by msg_type + content", parents=[shared])
    reply.add_argument("message_id", help="Original message_id")
    reply.add_argument("--msg-type", required=True, help="Feishu msg_type")
    reply.add_argument("--content-json", help="Message content JSON object string")
    reply.add_argument("--content-file", help="Message content JSON file path")
    reply.add_argument("--content-stdin", action="store_true", help="Read message content JSON from stdin")
    reply.add_argument("--uuid", help="Client message id for idempotency")
    reply.set_defaults(handler=_cmd_im_reply_generic)

    get_message = im_sub.add_parser("get", help="Get message detail", parents=[shared])
    get_message.add_argument("message_id", help="message_id")
    get_message.set_defaults(handler=_cmd_im_get)

    recall = im_sub.add_parser("recall", help="Recall a message", parents=[shared])
    recall.add_argument("message_id", help="message_id")
    recall.set_defaults(handler=_cmd_im_recall)

    push_follow_up = im_sub.add_parser(
        "push-follow-up",
        help="Add follow-up bubbles below a message",
        parents=[shared],
    )
    push_follow_up.add_argument("message_id", help="message_id")
    push_follow_up.add_argument("--follow-ups-json", help="Follow-up list JSON array string")
    push_follow_up.add_argument("--follow-ups-file", help="Follow-up list JSON file path")
    push_follow_up.add_argument("--follow-ups-stdin", action="store_true", help="Read follow-up list JSON from stdin")
    push_follow_up.set_defaults(handler=_cmd_im_push_follow_up)

    forward_thread = im_sub.add_parser("forward-thread", help="Forward thread to target", parents=[shared])
    forward_thread.add_argument("thread_id", help="thread_id")
    _add_receive_args(forward_thread)
    forward_thread.add_argument("--uuid", help="Request uuid for deduplication")
    forward_thread.set_defaults(handler=_cmd_im_forward_thread)

    update_url_previews = im_sub.add_parser(
        "update-url-previews",
        help="Batch update URL previews",
        parents=[shared],
    )
    update_url_previews.add_argument(
        "--preview-token",
        action="append",
        dest="preview_tokens",
        required=True,
        help="Preview token from url.preview.get event, repeatable",
    )
    update_url_previews.add_argument(
        "--open-id",
        action="append",
        dest="open_ids",
        help="Optional open_id filter, repeatable",
    )
    update_url_previews.set_defaults(handler=_cmd_im_update_url_previews)


def _build_media_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    shared: argparse.ArgumentParser,
) -> None:
    media_parser = subparsers.add_parser("media", help="Media upload/download")
    media_sub = media_parser.add_subparsers(dest="media_command")
    media_sub.required = True

    upload_image = media_sub.add_parser("upload-image", help="Upload image", parents=[shared])
    upload_image.add_argument("path", help="Image file path")
    upload_image.add_argument("--image-type", default="message", help="message/avatar")
    upload_image.set_defaults(handler=_cmd_media_upload_image)

    upload_file = media_sub.add_parser("upload-file", help="Upload file", parents=[shared])
    upload_file.add_argument("path", help="File path")
    upload_file.add_argument("--file-type", default="stream", help="stream/mp4/pdf/doc/xls/ppt/opus")
    upload_file.add_argument("--file-name", help="Override file name")
    upload_file.add_argument("--duration", type=int, help="Audio duration (ms)")
    upload_file.add_argument("--content-type", help="Override mime type")
    upload_file.set_defaults(handler=_cmd_media_upload_file)

    download_file = media_sub.add_parser("download-file", help="Download file by file_key", parents=[shared])
    download_file.add_argument("file_key", help="File key")
    download_file.add_argument("output", help="Output file path")
    download_file.set_defaults(handler=_cmd_media_download_file)


def _build_bitable_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    shared: argparse.ArgumentParser,
) -> None:
    bitable_parser = subparsers.add_parser("bitable", help="Bitable operations")
    bitable_sub = bitable_parser.add_subparsers(dest="bitable_command")
    bitable_sub.required = True

    create_from_csv = bitable_sub.add_parser(
        "create-from-csv",
        help="Create bitable app and table from CSV",
        parents=[shared],
    )
    create_from_csv.add_argument("csv_path", help="CSV file path")
    create_from_csv.add_argument("--app-name", required=True, help="Bitable app name")
    create_from_csv.add_argument("--table-name", required=True, help="Bitable table name")
    create_from_csv.add_argument("--grant-member-id", help="Optional member id to grant permission")
    create_from_csv.add_argument(
        "--member-id-type",
        default="open_id",
        help="open_id/user_id/union_id (default: open_id)",
    )
    create_from_csv.set_defaults(handler=_cmd_bitable_create_from_csv)

    create_table = bitable_sub.add_parser("create-table", help="Create table", parents=[shared])
    create_table.add_argument("--app-token", required=True, help="Bitable app_token")
    create_table.add_argument("--table-json", help="Table JSON object string")
    create_table.add_argument("--table-file", help="Table JSON file path")
    create_table.add_argument("--table-stdin", action="store_true", help="Read table JSON from stdin")
    create_table.set_defaults(handler=_cmd_bitable_create_table)

    create_record = bitable_sub.add_parser("create-record", help="Create record", parents=[shared])
    create_record.add_argument("--app-token", required=True, help="Bitable app_token")
    create_record.add_argument("--table-id", required=True, help="Bitable table_id")
    create_record.add_argument("--fields-json", help="Fields JSON object string")
    create_record.add_argument("--fields-file", help="Fields JSON file path")
    create_record.add_argument("--fields-stdin", action="store_true", help="Read fields JSON from stdin")
    create_record.add_argument("--user-id-type", help="Optional user_id_type")
    create_record.add_argument("--client-token", help="Optional client token")
    create_record.add_argument(
        "--ignore-consistency-check",
        action="store_true",
        help="Enable ignore_consistency_check",
    )
    create_record.set_defaults(handler=_cmd_bitable_create_record)

    list_records = bitable_sub.add_parser("list-records", help="List records", parents=[shared])
    list_records.add_argument("--app-token", required=True, help="Bitable app_token")
    list_records.add_argument("--table-id", required=True, help="Bitable table_id")
    list_records.add_argument("--page-size", type=int, help="Page size")
    list_records.add_argument("--page-token", help="Page token")
    list_records.set_defaults(handler=_cmd_bitable_list_records)

    grant_edit = bitable_sub.add_parser("grant-edit", help="Grant edit permission on bitable", parents=[shared])
    grant_edit.add_argument("--app-token", required=True, help="Bitable app_token")
    grant_edit.add_argument("--member-id", required=True, help="Member id")
    grant_edit.add_argument(
        "--member-id-type",
        default="open_id",
        help="open_id/user_id/union_id (default: open_id)",
    )
    grant_edit.set_defaults(handler=_cmd_bitable_grant_edit)


def _build_docx_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    shared: argparse.ArgumentParser,
) -> None:
    docx_parser = subparsers.add_parser("docx", help="Docx and docs content operations")
    docx_sub = docx_parser.add_subparsers(dest="docx_command")
    docx_sub.required = True

    create = docx_sub.add_parser("create", help="Create docx document", parents=[shared])
    create.add_argument("--title", required=True, help="Document title")
    create.set_defaults(handler=_cmd_docx_create)

    append_markdown = docx_sub.add_parser("append-markdown", help="Append markdown to docx", parents=[shared])
    append_markdown.add_argument("--document-id", required=True, help="Docx document_id")
    append_markdown.add_argument("--markdown", help="Markdown text")
    append_markdown.add_argument("--markdown-file", help="Markdown file path")
    append_markdown.add_argument("--markdown-stdin", action="store_true", help="Read markdown text from stdin")
    append_markdown.set_defaults(handler=_cmd_docx_append_markdown)

    create_from_markdown = docx_sub.add_parser(
        "create-from-markdown",
        help="Create docx and append markdown",
        parents=[shared],
    )
    create_from_markdown.add_argument("--title", required=True, help="Document title")
    create_from_markdown.add_argument("--markdown", help="Markdown text")
    create_from_markdown.add_argument("--markdown-file", help="Markdown file path")
    create_from_markdown.add_argument("--markdown-stdin", action="store_true", help="Read markdown text from stdin")
    create_from_markdown.set_defaults(handler=_cmd_docx_create_from_markdown)

    grant_edit = docx_sub.add_parser("grant-edit", help="Grant edit permission on docx", parents=[shared])
    grant_edit.add_argument("--document-id", required=True, help="Docx document_id")
    grant_edit.add_argument("--member-id", required=True, help="Member id")
    grant_edit.add_argument(
        "--member-id-type",
        default="open_id",
        help="open_id/user_id/union_id (default: open_id)",
    )
    grant_edit.set_defaults(handler=_cmd_docx_grant_edit)

    get_markdown = docx_sub.add_parser("get-markdown", help="Get markdown from docs content API", parents=[shared])
    get_markdown.add_argument("--doc-token", required=True, help="doc token")
    get_markdown.add_argument("--doc-type", default="docx", help="docx/sheet/bitable/file/wiki_doc/wiki_sheet")
    get_markdown.add_argument("--lang", help="Optional language")
    get_markdown.set_defaults(handler=_cmd_docx_get_markdown)


def _build_drive_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    shared: argparse.ArgumentParser,
) -> None:
    drive_parser = subparsers.add_parser("drive", help="Drive file and permission operations")
    drive_sub = drive_parser.add_subparsers(dest="drive_command")
    drive_sub.required = True

    upload_file = drive_sub.add_parser("upload-file", help="Upload file to drive", parents=[shared])
    upload_file.add_argument("path", help="File path")
    upload_file.add_argument("--parent-type", required=True, help="Parent type, e.g. explorer")
    upload_file.add_argument("--parent-node", required=True, help="Parent node token")
    upload_file.add_argument("--file-name", help="Override file name")
    upload_file.add_argument("--checksum", help="Optional checksum")
    upload_file.add_argument("--content-type", help="Optional mime type")
    upload_file.set_defaults(handler=_cmd_drive_upload_file)

    create_import = drive_sub.add_parser("create-import-task", help="Create drive import task", parents=[shared])
    create_import.add_argument("--task-json", help="Task JSON object string")
    create_import.add_argument("--task-file", help="Task JSON file path")
    create_import.add_argument("--task-stdin", action="store_true", help="Read task JSON from stdin")
    create_import.set_defaults(handler=_cmd_drive_create_import_task)

    get_import = drive_sub.add_parser("get-import-task", help="Get drive import task", parents=[shared])
    get_import.add_argument("ticket", help="Import task ticket")
    get_import.set_defaults(handler=_cmd_drive_get_import_task)

    create_export = drive_sub.add_parser("create-export-task", help="Create drive export task", parents=[shared])
    create_export.add_argument("--task-json", help="Task JSON object string")
    create_export.add_argument("--task-file", help="Task JSON file path")
    create_export.add_argument("--task-stdin", action="store_true", help="Read task JSON from stdin")
    create_export.set_defaults(handler=_cmd_drive_create_export_task)

    get_export = drive_sub.add_parser("get-export-task", help="Get drive export task", parents=[shared])
    get_export.add_argument("ticket", help="Export task ticket")
    get_export.add_argument("--token", help="Optional resource token")
    get_export.set_defaults(handler=_cmd_drive_get_export_task)

    grant_edit = drive_sub.add_parser("grant-edit", help="Grant edit permission", parents=[shared])
    grant_edit.add_argument("--token", required=True, help="Resource token")
    grant_edit.add_argument("--resource-type", required=True, help="Resource type, e.g. bitable/docx")
    grant_edit.add_argument("--member-id", required=True, help="Member id")
    grant_edit.add_argument(
        "--member-id-type",
        default="open_id",
        help="open_id/user_id/union_id (default: open_id)",
    )
    grant_edit.add_argument(
        "--permission",
        default="edit",
        help="Permission value (default: edit)",
    )
    grant_edit.set_defaults(handler=_cmd_drive_grant_edit)

    list_members = drive_sub.add_parser("list-members", help="List permission members", parents=[shared])
    list_members.add_argument("--token", required=True, help="Resource token")
    list_members.add_argument("--resource-type", required=True, help="Resource type, e.g. bitable/docx")
    list_members.add_argument("--fields", help="Optional fields")
    list_members.add_argument("--perm-type", help="Optional perm_type")
    list_members.set_defaults(handler=_cmd_drive_list_members)


def _build_wiki_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    shared: argparse.ArgumentParser,
) -> None:
    wiki_parser = subparsers.add_parser("wiki", help="Wiki operations")
    wiki_sub = wiki_parser.add_subparsers(dest="wiki_command")
    wiki_sub.required = True

    list_spaces = wiki_sub.add_parser("list-spaces", help="List wiki spaces", parents=[shared])
    list_spaces.add_argument("--page-size", type=int, help="Page size")
    list_spaces.add_argument("--page-token", help="Page token")
    list_spaces.set_defaults(handler=_cmd_wiki_list_spaces)

    search_nodes = wiki_sub.add_parser("search-nodes", help="Search wiki nodes", parents=[shared])
    search_nodes.add_argument("--query", required=True, help="Search query")
    search_nodes.add_argument("--space-id", help="Optional space id")
    search_nodes.add_argument("--node-id", help="Optional node id")
    search_nodes.add_argument("--page-size", type=int, help="Page size")
    search_nodes.add_argument("--page-token", help="Page token")
    search_nodes.set_defaults(handler=_cmd_wiki_search_nodes)

    get_node = wiki_sub.add_parser("get-node", help="Get wiki node by token", parents=[shared])
    get_node.add_argument("--token", required=True, help="Node token")
    get_node.add_argument("--obj-type", help="Optional object type")
    get_node.set_defaults(handler=_cmd_wiki_get_node)

    list_nodes = wiki_sub.add_parser("list-nodes", help="List nodes in a space", parents=[shared])
    list_nodes.add_argument("--space-id", required=True, help="Space id")
    list_nodes.add_argument("--parent-node-token", help="Optional parent node token")
    list_nodes.add_argument("--page-size", type=int, help="Page size")
    list_nodes.add_argument("--page-token", help="Page token")
    list_nodes.set_defaults(handler=_cmd_wiki_list_nodes)


def _build_calendar_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    shared: argparse.ArgumentParser,
) -> None:
    calendar_parser = subparsers.add_parser(
        "calendar",
        help="Calendar operations",
        description=(
            "Calendar operations.\n"
            "Tip: for event attachments, prefer `calendar attach-material` "
            "to avoid attachment token permission issues."
        ),
    )
    calendar_sub = calendar_parser.add_subparsers(dest="calendar_command")
    calendar_sub.required = True

    primary = calendar_sub.add_parser("primary", help="Get primary calendar", parents=[shared])
    primary.add_argument("--user-id-type", help="Optional user_id_type")
    primary.set_defaults(handler=_cmd_calendar_primary)

    list_calendars = calendar_sub.add_parser("list-calendars", help="List calendars", parents=[shared])
    list_calendars.add_argument("--page-size", type=int, help="Page size")
    list_calendars.add_argument("--page-token", help="Page token")
    list_calendars.add_argument("--sync-token", help="Sync token")
    list_calendars.set_defaults(handler=_cmd_calendar_list_calendars)

    get_calendar = calendar_sub.add_parser("get-calendar", help="Get calendar by id", parents=[shared])
    get_calendar.add_argument("--calendar-id", required=True, help="Calendar id")
    get_calendar.set_defaults(handler=_cmd_calendar_get_calendar)

    create_calendar = calendar_sub.add_parser("create-calendar", help="Create calendar", parents=[shared])
    create_calendar.add_argument("--calendar-json", help="Calendar JSON object string")
    create_calendar.add_argument("--calendar-file", help="Calendar JSON file path")
    create_calendar.add_argument("--calendar-stdin", action="store_true", help="Read calendar JSON from stdin")
    create_calendar.set_defaults(handler=_cmd_calendar_create_calendar)

    update_calendar = calendar_sub.add_parser("update-calendar", help="Update calendar", parents=[shared])
    update_calendar.add_argument("--calendar-id", required=True, help="Calendar id")
    update_calendar.add_argument("--calendar-json", help="Calendar JSON object string")
    update_calendar.add_argument("--calendar-file", help="Calendar JSON file path")
    update_calendar.add_argument("--calendar-stdin", action="store_true", help="Read calendar JSON from stdin")
    update_calendar.set_defaults(handler=_cmd_calendar_update_calendar)

    delete_calendar = calendar_sub.add_parser("delete-calendar", help="Delete calendar", parents=[shared])
    delete_calendar.add_argument("--calendar-id", required=True, help="Calendar id")
    delete_calendar.set_defaults(handler=_cmd_calendar_delete_calendar)

    search_calendars = calendar_sub.add_parser("search-calendars", help="Search calendars", parents=[shared])
    search_calendars.add_argument("--query", required=True, help="Search query")
    search_calendars.add_argument("--page-size", type=int, help="Page size")
    search_calendars.add_argument("--page-token", help="Page token")
    search_calendars.set_defaults(handler=_cmd_calendar_search_calendars)

    list_events = calendar_sub.add_parser("list-events", help="List events in a calendar", parents=[shared])
    list_events.add_argument("--calendar-id", required=True, help="Calendar id")
    list_events.add_argument("--page-size", type=int, help="Page size")
    list_events.add_argument("--page-token", help="Page token")
    list_events.add_argument("--sync-token", help="Sync token")
    list_events.add_argument("--start-time", help="Start time (unix seconds)")
    list_events.add_argument("--end-time", help="End time (unix seconds)")
    list_events.add_argument("--anchor-time", help="Anchor time (unix seconds)")
    list_events.add_argument("--user-id-type", help="Optional user_id_type")
    list_events.set_defaults(handler=_cmd_calendar_list_events)

    get_event = calendar_sub.add_parser("get-event", help="Get event by id", parents=[shared])
    get_event.add_argument("--calendar-id", required=True, help="Calendar id")
    get_event.add_argument("--event-id", required=True, help="Event id")
    get_event.add_argument("--need-attendee", action="store_true", help="Include attendees")
    get_event.add_argument("--need-meeting-settings", action="store_true", help="Include meeting settings")
    get_event.add_argument("--max-attendee-num", type=int, help="Max attendee count")
    get_event.add_argument("--user-id-type", help="Optional user_id_type")
    get_event.set_defaults(handler=_cmd_calendar_get_event)

    create_event = calendar_sub.add_parser("create-event", help="Create event", parents=[shared])
    create_event.add_argument("--calendar-id", required=True, help="Calendar id")
    create_event.add_argument("--event-json", help="Event JSON object string")
    create_event.add_argument("--event-file", help="Event JSON file path")
    create_event.add_argument("--event-stdin", action="store_true", help="Read event JSON from stdin")
    create_event.add_argument("--user-id-type", help="Optional user_id_type")
    create_event.add_argument("--idempotency-key", help="Optional idempotency key")
    create_event.set_defaults(handler=_cmd_calendar_create_event)

    update_event = calendar_sub.add_parser("update-event", help="Update event", parents=[shared])
    update_event.add_argument("--calendar-id", required=True, help="Calendar id")
    update_event.add_argument("--event-id", required=True, help="Event id")
    update_event.add_argument("--event-json", help="Event JSON object string")
    update_event.add_argument("--event-file", help="Event JSON file path")
    update_event.add_argument("--event-stdin", action="store_true", help="Read event JSON from stdin")
    update_event.add_argument("--user-id-type", help="Optional user_id_type")
    update_event.set_defaults(handler=_cmd_calendar_update_event)

    attach_material = calendar_sub.add_parser(
        "attach-material",
        help="Upload a file as calendar material and attach to event",
        parents=[shared],
        description=(
            "Upload material for a calendar event and update event attachments.\n"
            "This command auto uses `parent_type=calendar` and `parent_node=<calendar_id>` "
            "when uploading media."
        ),
    )
    attach_material.add_argument("--calendar-id", required=True, help="Calendar id")
    attach_material.add_argument("--event-id", required=True, help="Event id")
    attach_material.add_argument("--path", required=True, help="Local file path to upload")
    attach_material.add_argument("--file-name", help="Override uploaded file name")
    attach_material.add_argument("--content-type", help="Override file content type")
    attach_material.add_argument(
        "--mode",
        choices=("append", "replace"),
        default="append",
        help="append keeps existing attachments; replace overwrites all (default: append)",
    )
    attach_material.add_argument(
        "--need-notification",
        choices=("true", "false"),
        help="Whether to notify attendees on update",
    )
    attach_material.add_argument("--user-id-type", help="Optional user_id_type")
    attach_material.set_defaults(handler=_cmd_calendar_attach_material)

    delete_event = calendar_sub.add_parser("delete-event", help="Delete event", parents=[shared])
    delete_event.add_argument("--calendar-id", required=True, help="Calendar id")
    delete_event.add_argument("--event-id", required=True, help="Event id")
    delete_event.add_argument(
        "--need-notification",
        choices=("true", "false"),
        help="Whether to notify attendees",
    )
    delete_event.set_defaults(handler=_cmd_calendar_delete_event)

    search_events = calendar_sub.add_parser("search-events", help="Search events in a calendar", parents=[shared])
    search_events.add_argument("--calendar-id", required=True, help="Calendar id")
    search_events.add_argument("--query", required=True, help="Search query")
    search_events.add_argument("--filter-json", help="Search filter JSON object string")
    search_events.add_argument("--filter-file", help="Search filter JSON file path")
    search_events.add_argument("--filter-stdin", action="store_true", help="Read search filter JSON from stdin")
    search_events.add_argument("--page-size", type=int, help="Page size")
    search_events.add_argument("--page-token", help="Page token")
    search_events.add_argument("--user-id-type", help="Optional user_id_type")
    search_events.set_defaults(handler=_cmd_calendar_search_events)

    reply_event = calendar_sub.add_parser("reply-event", help="Reply to an event", parents=[shared])
    reply_event.add_argument("--calendar-id", required=True, help="Calendar id")
    reply_event.add_argument("--event-id", required=True, help="Event id")
    reply_event.add_argument("--reply-json", help="Reply JSON object string")
    reply_event.add_argument("--reply-file", help="Reply JSON file path")
    reply_event.add_argument("--reply-stdin", action="store_true", help="Read reply JSON from stdin")
    reply_event.set_defaults(handler=_cmd_calendar_reply_event)

    freebusy = calendar_sub.add_parser("list-freebusy", help="Query freebusy", parents=[shared])
    freebusy.add_argument("--request-json", help="Request JSON object string")
    freebusy.add_argument("--request-file", help="Request JSON file path")
    freebusy.add_argument("--request-stdin", action="store_true", help="Read request JSON from stdin")
    freebusy.add_argument("--user-id-type", help="Optional user_id_type")
    freebusy.set_defaults(handler=_cmd_calendar_list_freebusy)

    batch_freebusy = calendar_sub.add_parser("batch-freebusy", help="Query freebusy in batch", parents=[shared])
    batch_freebusy.add_argument("--request-json", help="Request JSON object string")
    batch_freebusy.add_argument("--request-file", help="Request JSON file path")
    batch_freebusy.add_argument("--request-stdin", action="store_true", help="Read request JSON from stdin")
    batch_freebusy.add_argument("--user-id-type", help="Optional user_id_type")
    batch_freebusy.set_defaults(handler=_cmd_calendar_batch_freebusy)

    caldav = calendar_sub.add_parser("generate-caldav-conf", help="Generate CalDAV config", parents=[shared])
    caldav.add_argument("--request-json", help="Request JSON object string")
    caldav.add_argument("--request-file", help="Request JSON file path")
    caldav.add_argument("--request-stdin", action="store_true", help="Read request JSON from stdin")
    caldav.set_defaults(handler=_cmd_calendar_generate_caldav_conf)


def _build_webhook_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    shared: argparse.ArgumentParser,
) -> None:
    webhook_parser = subparsers.add_parser("webhook", help="Webhook utility commands")
    webhook_sub = webhook_parser.add_subparsers(dest="webhook_command")
    webhook_sub.required = True

    decode = webhook_sub.add_parser("decode", help="Decode webhook body (supports encrypted payload)", parents=[shared])
    _add_webhook_body_args(decode)
    decode.add_argument("--encrypt-key", help="Encrypt key for encrypted payload")
    decode.set_defaults(handler=_cmd_webhook_decode)

    verify = webhook_sub.add_parser("verify-signature", help="Verify webhook signature headers", parents=[shared])
    verify.add_argument("--headers-json", help="Headers JSON object string")
    verify.add_argument("--headers-file", help="Headers JSON file path")
    verify.add_argument("--headers-stdin", action="store_true", help="Read headers JSON from stdin")
    _add_webhook_body_args(verify)
    verify.add_argument("--encrypt-key", help="Encrypt key used for signature")
    verify.add_argument(
        "--tolerance-seconds",
        type=float,
        default=300.0,
        help="Timestamp tolerance seconds (default: 300)",
    )
    verify.set_defaults(handler=_cmd_webhook_verify_signature)

    challenge = webhook_sub.add_parser("challenge", help="Build challenge response payload", parents=[shared])
    challenge.add_argument("--challenge", required=True, help="Challenge string")
    challenge.set_defaults(handler=_cmd_webhook_challenge)

    parse = webhook_sub.add_parser("parse", help="Parse webhook envelope", parents=[shared])
    _add_webhook_body_args(parse)
    parse.add_argument("--encrypt-key", help="Encrypt key for encrypted payload")
    parse.add_argument(
        "--is-callback",
        action="store_true",
        help="Parse as callback payload",
    )
    parse.add_argument(
        "--include-payload",
        action="store_true",
        help="Include decoded payload in output",
    )
    parse.set_defaults(handler=_cmd_webhook_parse)

    serve = webhook_sub.add_parser("serve", help="Run local webhook HTTP server", parents=[shared])
    serve.add_argument("--host", default="127.0.0.1", help="Listen host (default: 127.0.0.1)")
    serve.add_argument("--port", type=int, default=8000, help="Listen port (default: 8000)")
    serve.add_argument("--path", default="/webhook/feishu", help="Webhook path (default: /webhook/feishu)")
    serve.add_argument("--encrypt-key", help="Encrypt key for encrypted payload/signature")
    serve.add_argument(
        "--verification-token",
        help="Verification token for token check",
    )
    serve.add_argument(
        "--is-callback",
        action="store_true",
        help="Treat incoming payload as callback mode",
    )
    serve.add_argument(
        "--no-verify-signatures",
        action="store_true",
        help="Disable signature verification",
    )
    serve.add_argument(
        "--timestamp-tolerance-seconds",
        type=float,
        default=300.0,
        help="Signature timestamp tolerance in seconds (default: 300)",
    )
    serve.add_argument(
        "--print-payload",
        action="store_true",
        help="Print full payload for each event",
    )
    serve.add_argument(
        "--output-file",
        help="Append events as JSON lines to file",
    )
    serve.add_argument(
        "--event-type",
        action="append",
        dest="event_types",
        help="Register specific event type(s), can be repeated",
    )
    serve.add_argument(
        "--max-requests",
        type=int,
        help="Auto stop after handling N POST requests",
    )
    serve.set_defaults(handler=_cmd_webhook_serve)


def _build_ws_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    shared: argparse.ArgumentParser,
) -> None:
    ws_parser = subparsers.add_parser("ws", help="WebSocket long-connection utilities")
    ws_sub = ws_parser.add_subparsers(dest="ws_command")
    ws_sub.required = True

    endpoint = ws_sub.add_parser("endpoint", help="Fetch long-connection endpoint", parents=[shared])
    endpoint.add_argument(
        "--domain",
        help="Open platform domain, default: https://open.feishu.cn",
    )
    endpoint.set_defaults(handler=_cmd_ws_endpoint)

    run = ws_sub.add_parser("run", help="Run low-level WS listener", parents=[shared])
    run.add_argument(
        "--domain",
        help="Open platform domain, default: https://open.feishu.cn",
    )
    run.add_argument(
        "--event-type",
        action="append",
        dest="event_types",
        help="Register specific event type(s), can be repeated",
    )
    run.add_argument(
        "--print-payload",
        action="store_true",
        help="Print full payload for each event",
    )
    run.add_argument(
        "--output-file",
        help="Append events as JSON lines to file",
    )
    run.add_argument(
        "--max-events",
        type=int,
        help="Auto stop after receiving N events",
    )
    run.add_argument(
        "--duration-seconds",
        type=float,
        help="Auto stop after duration seconds",
    )
    run.set_defaults(handler=_cmd_ws_run)


def _build_server_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    shared: argparse.ArgumentParser,
) -> None:
    server_parser = subparsers.add_parser("server", help="Feishu bot long-connection server")
    server_sub = server_parser.add_subparsers(dest="server_command")
    server_sub.required = True

    run = server_sub.add_parser("run", help="Run long-connection server", parents=[shared])
    run.add_argument(
        "--domain",
        help="Open platform domain, default: https://open.feishu.cn",
    )
    run.add_argument(
        "--event-type",
        action="append",
        dest="event_types",
        help="Register specific event type(s), can be repeated",
    )
    run.add_argument(
        "--print-payload",
        action="store_true",
        help="Print full payload for each event",
    )
    run.add_argument(
        "--output-file",
        help="Append events as JSON lines to file",
    )
    run.add_argument(
        "--max-events",
        type=int,
        help="Auto stop after receiving N events",
    )
    run.add_argument(
        "--no-handle-signals",
        action="store_true",
        help="Disable SIGINT/SIGTERM handling in server.run()",
    )
    run.set_defaults(handler=_cmd_server_run)

    start = server_sub.add_parser("start", help="Start server in background", parents=[shared])
    start.add_argument(
        "--domain",
        help="Open platform domain, default: https://open.feishu.cn",
    )
    start.add_argument(
        "--event-type",
        action="append",
        dest="event_types",
        help="Register specific event type(s), can be repeated",
    )
    start.add_argument(
        "--print-payload",
        action="store_true",
        help="Print full payload for each event",
    )
    start.add_argument(
        "--output-file",
        help="Append events as JSON lines to file",
    )
    start.add_argument(
        "--max-events",
        type=int,
        help="Auto stop after receiving N events",
    )
    start.add_argument(
        "--pid-file",
        default=".feishu_server.pid",
        help="PID file path (default: .feishu_server.pid)",
    )
    start.add_argument(
        "--log-file",
        help="Redirect server stdout/stderr to this file",
    )
    start.set_defaults(handler=_cmd_server_start)

    status = server_sub.add_parser("status", help="Check background server status", parents=[shared])
    status.add_argument(
        "--pid-file",
        default=".feishu_server.pid",
        help="PID file path (default: .feishu_server.pid)",
    )
    status.set_defaults(handler=_cmd_server_status)

    stop = server_sub.add_parser("stop", help="Stop background server", parents=[shared])
    stop.add_argument(
        "--pid-file",
        default=".feishu_server.pid",
        help="PID file path (default: .feishu_server.pid)",
    )
    stop.set_defaults(handler=_cmd_server_stop)


def _add_receive_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--receive-id", required=True, help="receive_id")
    parser.add_argument(
        "--receive-id-type",
        default="open_id",
        help="open_id/user_id/union_id/email/chat_id (default: open_id)",
    )


def _add_webhook_body_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--body-json", help="Raw webhook body JSON string")
    parser.add_argument("--body-file", help="Raw webhook body file path")
    parser.add_argument("--body-stdin", action="store_true", help="Read raw webhook body JSON from stdin")


def _cmd_auth_token(args: argparse.Namespace) -> Mapping[str, Any]:
    client = _build_client(args)
    return {
        "auth_mode": client.config.auth_mode,
        "access_token": client.get_access_token(),
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
    client = _build_client(args)
    url = client.build_authorize_url(
        redirect_uri=str(args.redirect_uri),
        scope=getattr(args, "scope", None),
        state=getattr(args, "state", None),
    )
    return {"authorize_url": url}


def _cmd_oauth_exchange_code(args: argparse.Namespace) -> Any:
    client = _build_client(args)
    return client.exchange_authorization_code(
        str(args.code),
        grant_type=str(args.grant_type),
    )


def _cmd_oauth_refresh_token(args: argparse.Namespace) -> Any:
    client = _build_client(args)
    return client.refresh_user_access_token(refresh_token=getattr(args, "refresh_token", None))


def _cmd_oauth_user_info(args: argparse.Namespace) -> Any:
    client = _build_client(args)
    return client.get_user_info(user_access_token=getattr(args, "user_access_token", None))


def _cmd_bot_info(args: argparse.Namespace) -> Any:
    service = BotService(_build_client(args))
    return service.get_info()


def _cmd_im_send_text(args: argparse.Namespace) -> Any:
    service = MessageService(_build_client(args))
    return service.send_text(
        receive_id_type=str(args.receive_id_type),
        receive_id=str(args.receive_id),
        text=str(args.text),
        uuid=getattr(args, "uuid", None),
    )


def _cmd_im_send_markdown(args: argparse.Namespace) -> Any:
    markdown = _resolve_text_input(
        text=getattr(args, "markdown", None),
        file_path=getattr(args, "markdown_file", None),
        stdin_enabled=bool(getattr(args, "markdown_stdin", False)),
        name="markdown",
    )
    service = MessageService(_build_client(args))
    return service.send_markdown(
        receive_id_type=str(args.receive_id_type),
        receive_id=str(args.receive_id),
        markdown=markdown,
        locale=str(args.locale),
        title=getattr(args, "title", None),
        uuid=getattr(args, "uuid", None),
    )


def _cmd_im_reply_markdown(args: argparse.Namespace) -> Any:
    markdown = _resolve_text_input(
        text=getattr(args, "markdown", None),
        file_path=getattr(args, "markdown_file", None),
        stdin_enabled=bool(getattr(args, "markdown_stdin", False)),
        name="markdown",
    )
    service = MessageService(_build_client(args))
    return service.reply_markdown(
        str(args.message_id),
        markdown,
        locale=str(args.locale),
        title=getattr(args, "title", None),
        uuid=getattr(args, "uuid", None),
    )


def _cmd_im_send_generic(args: argparse.Namespace) -> Any:
    content = _parse_json_object(
        json_text=getattr(args, "content_json", None),
        file_path=getattr(args, "content_file", None),
        stdin_enabled=bool(getattr(args, "content_stdin", False)),
        name="content",
        required=True,
    )
    service = MessageService(_build_client(args))
    return service.send(
        receive_id_type=str(args.receive_id_type),
        receive_id=str(args.receive_id),
        msg_type=str(args.msg_type),
        content=content,
        uuid=getattr(args, "uuid", None),
    )


def _cmd_im_reply_generic(args: argparse.Namespace) -> Any:
    content = _parse_json_object(
        json_text=getattr(args, "content_json", None),
        file_path=getattr(args, "content_file", None),
        stdin_enabled=bool(getattr(args, "content_stdin", False)),
        name="content",
        required=True,
    )
    service = MessageService(_build_client(args))
    return service.reply(
        str(args.message_id),
        msg_type=str(args.msg_type),
        content=content,
        uuid=getattr(args, "uuid", None),
    )


def _cmd_im_get(args: argparse.Namespace) -> Any:
    service = MessageService(_build_client(args))
    return service.get(str(args.message_id))


def _cmd_im_recall(args: argparse.Namespace) -> Mapping[str, bool]:
    service = MessageService(_build_client(args))
    service.recall(str(args.message_id))
    return {"ok": True}


def _cmd_im_push_follow_up(args: argparse.Namespace) -> Any:
    follow_ups_raw = _parse_json_array(
        json_text=getattr(args, "follow_ups_json", None),
        file_path=getattr(args, "follow_ups_file", None),
        stdin_enabled=bool(getattr(args, "follow_ups_stdin", False)),
        name="follow-ups",
        required=True,
    )
    follow_ups: list[Mapping[str, Any]] = []
    for item in follow_ups_raw:
        if not isinstance(item, Mapping):
            raise ValueError("follow-ups must be a JSON array of objects")
        follow_ups.append({str(key): value for key, value in item.items()})
    service = MessageService(_build_client(args))
    return service.push_follow_up(str(args.message_id), follow_ups=follow_ups)


def _cmd_im_forward_thread(args: argparse.Namespace) -> Any:
    service = MessageService(_build_client(args))
    return service.forward_thread(
        str(args.thread_id),
        receive_id_type=str(args.receive_id_type),
        receive_id=str(args.receive_id),
        uuid=getattr(args, "uuid", None),
    )


def _cmd_im_update_url_previews(args: argparse.Namespace) -> Any:
    service = MessageService(_build_client(args))
    open_ids = list(getattr(args, "open_ids", []) or [])
    return service.batch_update_url_previews(
        preview_tokens=list(args.preview_tokens),
        open_ids=open_ids or None,
    )


def _cmd_media_upload_image(args: argparse.Namespace) -> Mapping[str, Any]:
    service = MediaService(_build_client(args))
    return service.upload_image(str(args.path), image_type=str(args.image_type))


def _cmd_media_upload_file(args: argparse.Namespace) -> Mapping[str, Any]:
    service = MediaService(_build_client(args))
    return service.upload_file(
        str(args.path),
        file_type=str(args.file_type),
        file_name=getattr(args, "file_name", None),
        duration=getattr(args, "duration", None),
        content_type=getattr(args, "content_type", None),
    )


def _cmd_media_download_file(args: argparse.Namespace) -> Mapping[str, Any]:
    service = MediaService(_build_client(args))
    content = service.download_file(str(args.file_key))
    output_path = Path(str(args.output))
    if output_path.parent and not output_path.parent.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(content)
    return {
        "ok": True,
        "file_key": str(args.file_key),
        "output": str(output_path),
        "size": len(content),
    }


def _cmd_bitable_create_from_csv(args: argparse.Namespace) -> Mapping[str, Any]:
    service = BitableService(_build_client(args))
    app_token, app_url = service.create_from_csv(
        str(args.csv_path),
        str(args.app_name),
        str(args.table_name),
    )
    granted = False
    member_id = getattr(args, "grant_member_id", None)
    if member_id:
        service.grant_edit_permission(
            app_token,
            str(member_id),
            str(args.member_id_type),
        )
        granted = True
    return {"app_token": app_token, "app_url": app_url, "granted": granted}


def _cmd_bitable_create_table(args: argparse.Namespace) -> Mapping[str, Any]:
    table = _parse_json_object(
        json_text=getattr(args, "table_json", None),
        file_path=getattr(args, "table_file", None),
        stdin_enabled=bool(getattr(args, "table_stdin", False)),
        name="table",
        required=True,
    )
    service = BitableService(_build_client(args))
    return service.create_table(str(args.app_token), table)


def _cmd_bitable_create_record(args: argparse.Namespace) -> Mapping[str, Any]:
    fields = _parse_json_object(
        json_text=getattr(args, "fields_json", None),
        file_path=getattr(args, "fields_file", None),
        stdin_enabled=bool(getattr(args, "fields_stdin", False)),
        name="fields",
        required=True,
    )
    service = BitableService(_build_client(args))
    return service.create_record(
        str(args.app_token),
        str(args.table_id),
        fields,
        user_id_type=getattr(args, "user_id_type", None),
        client_token=getattr(args, "client_token", None),
        ignore_consistency_check=bool(getattr(args, "ignore_consistency_check", False)),
    )


def _cmd_bitable_list_records(args: argparse.Namespace) -> Mapping[str, Any]:
    service = BitableService(_build_client(args))
    return service.list_records(
        str(args.app_token),
        str(args.table_id),
        page_size=getattr(args, "page_size", None),
        page_token=getattr(args, "page_token", None),
    )


def _cmd_bitable_grant_edit(args: argparse.Namespace) -> Mapping[str, bool]:
    service = BitableService(_build_client(args))
    service.grant_edit_permission(
        str(args.app_token),
        str(args.member_id),
        str(args.member_id_type),
    )
    return {"ok": True}


def _cmd_docx_create(args: argparse.Namespace) -> Mapping[str, Any]:
    service = DocxService(_build_client(args))
    document_id, url = service.create_document(str(args.title))
    return {"document_id": document_id, "url": url}


def _cmd_docx_append_markdown(args: argparse.Namespace) -> Mapping[str, bool]:
    markdown = _resolve_text_input(
        text=getattr(args, "markdown", None),
        file_path=getattr(args, "markdown_file", None),
        stdin_enabled=bool(getattr(args, "markdown_stdin", False)),
        name="markdown",
    )
    service = DocxService(_build_client(args))
    service.append_markdown(str(args.document_id), markdown)
    return {"ok": True}


def _cmd_docx_create_from_markdown(args: argparse.Namespace) -> Mapping[str, Any]:
    markdown = _resolve_text_input(
        text=getattr(args, "markdown", None),
        file_path=getattr(args, "markdown_file", None),
        stdin_enabled=bool(getattr(args, "markdown_stdin", False)),
        name="markdown",
    )
    service = DocxService(_build_client(args))
    document_id, url = service.create_document(str(args.title))
    service.append_markdown(document_id, markdown)
    return {"document_id": document_id, "url": url}


def _cmd_docx_grant_edit(args: argparse.Namespace) -> Mapping[str, bool]:
    service = DocxService(_build_client(args))
    service.grant_edit_permission(
        str(args.document_id),
        str(args.member_id),
        str(args.member_id_type),
    )
    return {"ok": True}


def _cmd_docx_get_markdown(args: argparse.Namespace) -> Mapping[str, str]:
    service = DocContentService(_build_client(args))
    markdown = service.get_markdown(
        str(args.doc_token),
        doc_type=str(args.doc_type),
        lang=getattr(args, "lang", None),
    )
    return {"markdown": markdown}


def _cmd_drive_upload_file(args: argparse.Namespace) -> Mapping[str, Any]:
    service = DriveFileService(_build_client(args))
    return service.upload_file(
        str(args.path),
        parent_type=str(args.parent_type),
        parent_node=str(args.parent_node),
        file_name=getattr(args, "file_name", None),
        checksum=getattr(args, "checksum", None),
        content_type=getattr(args, "content_type", None),
    )


def _cmd_drive_create_import_task(args: argparse.Namespace) -> Mapping[str, Any]:
    task = _parse_json_object(
        json_text=getattr(args, "task_json", None),
        file_path=getattr(args, "task_file", None),
        stdin_enabled=bool(getattr(args, "task_stdin", False)),
        name="task",
        required=True,
    )
    service = DriveFileService(_build_client(args))
    return service.create_import_task(task)


def _cmd_drive_get_import_task(args: argparse.Namespace) -> Mapping[str, Any]:
    service = DriveFileService(_build_client(args))
    return service.get_import_task(str(args.ticket))


def _cmd_drive_create_export_task(args: argparse.Namespace) -> Mapping[str, Any]:
    task = _parse_json_object(
        json_text=getattr(args, "task_json", None),
        file_path=getattr(args, "task_file", None),
        stdin_enabled=bool(getattr(args, "task_stdin", False)),
        name="task",
        required=True,
    )
    service = DriveFileService(_build_client(args))
    return service.create_export_task(task)


def _cmd_drive_get_export_task(args: argparse.Namespace) -> Mapping[str, Any]:
    service = DriveFileService(_build_client(args))
    return service.get_export_task(str(args.ticket), token=getattr(args, "token", None))


def _cmd_drive_grant_edit(args: argparse.Namespace) -> Mapping[str, bool]:
    service = DrivePermissionService(_build_client(args))
    service.grant_edit_permission(
        str(args.token),
        str(args.member_id),
        str(args.member_id_type),
        resource_type=str(args.resource_type),
        permission=str(args.permission),
    )
    return {"ok": True}


def _cmd_drive_list_members(args: argparse.Namespace) -> Mapping[str, Any]:
    service = DrivePermissionService(_build_client(args))
    return service.list_members(
        str(args.token),
        resource_type=str(args.resource_type),
        fields=getattr(args, "fields", None),
        perm_type=getattr(args, "perm_type", None),
    )


def _cmd_wiki_list_spaces(args: argparse.Namespace) -> Mapping[str, Any]:
    service = WikiService(_build_client(args))
    return service.list_spaces(
        page_size=getattr(args, "page_size", None),
        page_token=getattr(args, "page_token", None),
    )


def _cmd_wiki_search_nodes(args: argparse.Namespace) -> Mapping[str, Any]:
    service = WikiService(_build_client(args))
    return service.search_nodes(
        str(args.query),
        space_id=getattr(args, "space_id", None),
        node_id=getattr(args, "node_id", None),
        page_size=getattr(args, "page_size", None),
        page_token=getattr(args, "page_token", None),
    )


def _cmd_wiki_get_node(args: argparse.Namespace) -> Mapping[str, Any]:
    service = WikiService(_build_client(args))
    return service.get_node(str(args.token), obj_type=getattr(args, "obj_type", None))


def _cmd_wiki_list_nodes(args: argparse.Namespace) -> Mapping[str, Any]:
    service = WikiService(_build_client(args))
    return service.list_nodes(
        str(args.space_id),
        parent_node_token=getattr(args, "parent_node_token", None),
        page_size=getattr(args, "page_size", None),
        page_token=getattr(args, "page_token", None),
    )


def _cmd_calendar_primary(args: argparse.Namespace) -> Mapping[str, Any]:
    service = CalendarService(_build_client(args))
    return service.primary_calendar(user_id_type=getattr(args, "user_id_type", None))


def _cmd_calendar_list_calendars(args: argparse.Namespace) -> Mapping[str, Any]:
    service = CalendarService(_build_client(args))
    return service.list_calendars(
        page_size=getattr(args, "page_size", None),
        page_token=getattr(args, "page_token", None),
        sync_token=getattr(args, "sync_token", None),
    )


def _cmd_calendar_get_calendar(args: argparse.Namespace) -> Mapping[str, Any]:
    service = CalendarService(_build_client(args))
    return service.get_calendar(str(args.calendar_id))


def _cmd_calendar_create_calendar(args: argparse.Namespace) -> Mapping[str, Any]:
    calendar = _parse_json_object(
        json_text=getattr(args, "calendar_json", None),
        file_path=getattr(args, "calendar_file", None),
        stdin_enabled=bool(getattr(args, "calendar_stdin", False)),
        name="calendar",
        required=True,
    )
    service = CalendarService(_build_client(args))
    return service.create_calendar(calendar)


def _cmd_calendar_update_calendar(args: argparse.Namespace) -> Mapping[str, Any]:
    calendar = _parse_json_object(
        json_text=getattr(args, "calendar_json", None),
        file_path=getattr(args, "calendar_file", None),
        stdin_enabled=bool(getattr(args, "calendar_stdin", False)),
        name="calendar",
        required=True,
    )
    service = CalendarService(_build_client(args))
    return service.update_calendar(str(args.calendar_id), calendar)


def _cmd_calendar_delete_calendar(args: argparse.Namespace) -> Mapping[str, Any]:
    service = CalendarService(_build_client(args))
    return service.delete_calendar(str(args.calendar_id))


def _cmd_calendar_search_calendars(args: argparse.Namespace) -> Mapping[str, Any]:
    service = CalendarService(_build_client(args))
    return service.search_calendars(
        str(args.query),
        page_size=getattr(args, "page_size", None),
        page_token=getattr(args, "page_token", None),
    )


def _cmd_calendar_list_events(args: argparse.Namespace) -> Mapping[str, Any]:
    service = CalendarService(_build_client(args))
    return service.list_events(
        str(args.calendar_id),
        page_size=getattr(args, "page_size", None),
        page_token=getattr(args, "page_token", None),
        sync_token=getattr(args, "sync_token", None),
        start_time=getattr(args, "start_time", None),
        end_time=getattr(args, "end_time", None),
        anchor_time=getattr(args, "anchor_time", None),
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_calendar_get_event(args: argparse.Namespace) -> Mapping[str, Any]:
    service = CalendarService(_build_client(args))
    return service.get_event(
        str(args.calendar_id),
        str(args.event_id),
        need_meeting_settings=True if bool(getattr(args, "need_meeting_settings", False)) else None,
        need_attendee=True if bool(getattr(args, "need_attendee", False)) else None,
        max_attendee_num=getattr(args, "max_attendee_num", None),
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_calendar_create_event(args: argparse.Namespace) -> Mapping[str, Any]:
    event = _parse_json_object(
        json_text=getattr(args, "event_json", None),
        file_path=getattr(args, "event_file", None),
        stdin_enabled=bool(getattr(args, "event_stdin", False)),
        name="event",
        required=True,
    )
    service = CalendarService(_build_client(args))
    return service.create_event(
        str(args.calendar_id),
        event,
        user_id_type=getattr(args, "user_id_type", None),
        idempotency_key=getattr(args, "idempotency_key", None),
    )


def _cmd_calendar_update_event(args: argparse.Namespace) -> Mapping[str, Any]:
    event = _parse_json_object(
        json_text=getattr(args, "event_json", None),
        file_path=getattr(args, "event_file", None),
        stdin_enabled=bool(getattr(args, "event_stdin", False)),
        name="event",
        required=True,
    )
    service = CalendarService(_build_client(args))
    return service.update_event(
        str(args.calendar_id),
        str(args.event_id),
        event,
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_calendar_attach_material(args: argparse.Namespace) -> Mapping[str, Any]:
    calendar_id = str(args.calendar_id)
    event_id = str(args.event_id)
    mode = str(getattr(args, "mode", "append")).strip().lower()
    need_notification_raw = getattr(args, "need_notification", None)
    need_notification: Optional[bool]
    if need_notification_raw is None:
        need_notification = None
    else:
        need_notification = str(need_notification_raw).lower() == "true"

    client = _build_client(args)
    drive = DriveFileService(client)
    calendar = CalendarService(client)

    upload_result = drive.upload_media(
        str(args.path),
        parent_type="calendar",
        parent_node=calendar_id,
        file_name=getattr(args, "file_name", None),
        content_type=getattr(args, "content_type", None),
    )
    upload_data = _extract_response_data(upload_result)
    file_token_value = upload_data.get("file_token")
    if not isinstance(file_token_value, str) or not file_token_value:
        raise ValueError("upload material succeeded but file_token is missing in response")
    file_token = file_token_value

    attachments: list[dict[str, Any]] = []
    if mode == "append":
        event_result = calendar.get_event(
            calendar_id,
            event_id,
            user_id_type=getattr(args, "user_id_type", None),
        )
        event_data = _extract_response_data(event_result)
        event_payload = event_data.get("event")
        if isinstance(event_payload, Mapping):
            attachments = _normalize_calendar_attachments(event_payload.get("attachments"))

    attachment_name = upload_data.get("name")
    if not isinstance(attachment_name, str) or not attachment_name:
        attachment_name = getattr(args, "file_name", None)
    attachments = _merge_calendar_attachment(
        attachments,
        file_token=file_token,
        name=attachment_name,
    )

    event_payload: dict[str, object] = {"attachments": attachments}
    if need_notification is not None:
        event_payload["need_notification"] = need_notification

    update_result = calendar.update_event(
        calendar_id,
        event_id,
        event_payload,
        user_id_type=getattr(args, "user_id_type", None),
    )
    update_data = _extract_response_data(update_result)
    update_event_raw = update_data.get("event")
    updated_event_payload = (
        {str(key): value for key, value in update_event_raw.items()}
        if isinstance(update_event_raw, Mapping)
        else {}
    )

    return {
        "calendar_id": calendar_id,
        "event_id": event_id,
        "mode": mode,
        "file_token": file_token,
        "uploaded_name": attachment_name,
        "attachments_count": len(attachments),
        "attachments": attachments,
        "updated_event": updated_event_payload,
    }


def _cmd_calendar_delete_event(args: argparse.Namespace) -> Mapping[str, Any]:
    raw_need_notification = getattr(args, "need_notification", None)
    need_notification: Optional[bool]
    if raw_need_notification is None:
        need_notification = None
    else:
        need_notification = str(raw_need_notification).lower() == "true"
    service = CalendarService(_build_client(args))
    return service.delete_event(
        str(args.calendar_id),
        str(args.event_id),
        need_notification=need_notification,
    )


def _cmd_calendar_search_events(args: argparse.Namespace) -> Mapping[str, Any]:
    search_filter = _parse_json_object(
        json_text=getattr(args, "filter_json", None),
        file_path=getattr(args, "filter_file", None),
        stdin_enabled=bool(getattr(args, "filter_stdin", False)),
        name="filter",
        required=False,
    )
    service = CalendarService(_build_client(args))
    return service.search_events(
        str(args.calendar_id),
        str(args.query),
        page_size=getattr(args, "page_size", None),
        page_token=getattr(args, "page_token", None),
        user_id_type=getattr(args, "user_id_type", None),
        search_filter=search_filter or None,
    )


def _cmd_calendar_reply_event(args: argparse.Namespace) -> Mapping[str, Any]:
    reply = _parse_json_object(
        json_text=getattr(args, "reply_json", None),
        file_path=getattr(args, "reply_file", None),
        stdin_enabled=bool(getattr(args, "reply_stdin", False)),
        name="reply",
        required=True,
    )
    service = CalendarService(_build_client(args))
    return service.reply_event(str(args.calendar_id), str(args.event_id), reply)


def _cmd_calendar_list_freebusy(args: argparse.Namespace) -> Mapping[str, Any]:
    request = _parse_json_object(
        json_text=getattr(args, "request_json", None),
        file_path=getattr(args, "request_file", None),
        stdin_enabled=bool(getattr(args, "request_stdin", False)),
        name="request",
        required=True,
    )
    service = CalendarService(_build_client(args))
    return service.list_freebusy(request, user_id_type=getattr(args, "user_id_type", None))


def _cmd_calendar_batch_freebusy(args: argparse.Namespace) -> Mapping[str, Any]:
    request = _parse_json_object(
        json_text=getattr(args, "request_json", None),
        file_path=getattr(args, "request_file", None),
        stdin_enabled=bool(getattr(args, "request_stdin", False)),
        name="request",
        required=True,
    )
    service = CalendarService(_build_client(args))
    return service.batch_freebusy(request, user_id_type=getattr(args, "user_id_type", None))


def _cmd_calendar_generate_caldav_conf(args: argparse.Namespace) -> Mapping[str, Any]:
    request = _parse_json_object(
        json_text=getattr(args, "request_json", None),
        file_path=getattr(args, "request_file", None),
        stdin_enabled=bool(getattr(args, "request_stdin", False)),
        name="request",
        required=True,
    )
    service = CalendarService(_build_client(args))
    return service.generate_caldav_conf(request)


def _cmd_webhook_decode(args: argparse.Namespace) -> Mapping[str, Any]:
    raw_body = _resolve_raw_body(
        body_json=getattr(args, "body_json", None),
        body_file=getattr(args, "body_file", None),
        stdin_enabled=bool(getattr(args, "body_stdin", False)),
    )
    encrypt_key = _resolve_encrypt_key(args, required=False)
    return decode_webhook_body(raw_body, encrypt_key=encrypt_key)


def _cmd_webhook_verify_signature(args: argparse.Namespace) -> Mapping[str, bool]:
    headers = _parse_json_object(
        json_text=getattr(args, "headers_json", None),
        file_path=getattr(args, "headers_file", None),
        stdin_enabled=bool(getattr(args, "headers_stdin", False)),
        name="headers",
        required=True,
    )
    raw_body = _resolve_raw_body(
        body_json=getattr(args, "body_json", None),
        body_file=getattr(args, "body_file", None),
        stdin_enabled=bool(getattr(args, "body_stdin", False)),
    )
    encrypt_key = _resolve_encrypt_key(args, required=True)
    if encrypt_key is None:
        raise ConfigurationError("missing encrypt key: set FEISHU_ENCRYPT_KEY or pass --encrypt-key")
    normalized_headers = {str(key): str(value) for key, value in headers.items()}
    verify_signature(
        normalized_headers,
        raw_body,
        encrypt_key=encrypt_key,
        tolerance_seconds=float(args.tolerance_seconds),
    )
    return {"ok": True}


def _cmd_webhook_challenge(args: argparse.Namespace) -> Mapping[str, str]:
    return build_challenge_response(str(args.challenge))


def _cmd_webhook_parse(args: argparse.Namespace) -> Mapping[str, Any]:
    raw_body = _resolve_raw_body(
        body_json=getattr(args, "body_json", None),
        body_file=getattr(args, "body_file", None),
        stdin_enabled=bool(getattr(args, "body_stdin", False)),
    )
    encrypt_key = _resolve_encrypt_key(args, required=False)
    payload = decode_webhook_body(raw_body, encrypt_key=encrypt_key)
    envelope = parse_event_envelope(payload, is_callback=bool(getattr(args, "is_callback", False)))
    result: dict[str, Any] = {
        "schema": envelope.schema,
        "event_type": envelope.event_type,
        "event_id": envelope.event_id,
        "token": envelope.token,
        "tenant_key": envelope.tenant_key,
        "app_id": envelope.app_id,
        "create_time": envelope.create_time,
        "challenge": envelope.challenge,
        "is_callback": envelope.is_callback,
        "is_url_verification": envelope.is_url_verification,
    }
    if getattr(args, "include_payload", False):
        result["payload"] = payload
    return result


def _cmd_webhook_serve(args: argparse.Namespace) -> Mapping[str, Any]:
    output_format = str(args.output_format)
    output_file = _resolve_output_path(getattr(args, "output_file", None))
    max_requests = _validate_positive_int(getattr(args, "max_requests", None), name="max-requests")
    path = _normalize_server_path(str(args.path))

    registry = FeishuEventRegistry()
    event_types = [str(item) for item in list(getattr(args, "event_types", []) or [])]

    def _on_event(ctx: Any) -> None:
        event = _build_event_view(ctx, include_payload=bool(getattr(args, "print_payload", False)))
        _emit_event(event, output_format=output_format, output_file=output_file)
        return None

    if event_types:
        for event_type in event_types:
            registry.register(event_type, _on_event)
    else:
        registry.register_default(_on_event)

    receiver = WebhookReceiver(
        registry,
        encrypt_key=_resolve_encrypt_key(args, required=False),
        verification_token=(
            getattr(args, "verification_token", None)
            or os.getenv("FEISHU_VERIFICATION_TOKEN")
            or os.getenv("FEISHU_EVENT_VERIFICATION_TOKEN")
        ),
        is_callback=bool(getattr(args, "is_callback", False)),
        verify_signatures=not bool(getattr(args, "no_verify_signatures", False)),
        timestamp_tolerance_seconds=float(getattr(args, "timestamp_tolerance_seconds", 300.0)),
    )

    _serve_webhook_http(
        receiver=receiver,
        host=str(args.host),
        port=int(args.port),
        path=path,
        output_format=output_format,
        max_requests=max_requests,
    )
    return {"ok": True}


def _cmd_ws_endpoint(args: argparse.Namespace) -> Mapping[str, Any]:
    app_id, app_secret = _resolve_app_credentials(args)
    domain = _resolve_open_domain(args)
    endpoint = fetch_ws_endpoint(
        app_id=app_id,
        app_secret=app_secret,
        domain=domain,
        timeout_seconds=_resolve_timeout_seconds(args),
    )
    return {
        "url": endpoint.url,
        "device_id": endpoint.device_id,
        "service_id": endpoint.service_id,
        "remote_config": {
            "reconnect_count": endpoint.remote_config.reconnect_count,
            "reconnect_interval_seconds": endpoint.remote_config.reconnect_interval_seconds,
            "reconnect_nonce_seconds": endpoint.remote_config.reconnect_nonce_seconds,
            "ping_interval_seconds": endpoint.remote_config.ping_interval_seconds,
        },
    }


def _cmd_ws_run(args: argparse.Namespace) -> Mapping[str, Any]:
    app_id, app_secret = _resolve_app_credentials(args)
    output_file = _resolve_output_path(getattr(args, "output_file", None))
    max_events = _validate_max_events(getattr(args, "max_events", None))
    duration_seconds = _validate_duration(getattr(args, "duration_seconds", None))
    output_format = str(args.output_format)
    print_payload = bool(getattr(args, "print_payload", False))
    event_types = [str(item) for item in list(getattr(args, "event_types", []) or [])]
    events_count = asyncio.run(
        _run_ws_listener(
            app_id=app_id,
            app_secret=app_secret,
            domain=_resolve_open_domain(args),
            timeout_seconds=_resolve_timeout_seconds(args),
            output_format=output_format,
            output_file=output_file,
            print_payload=print_payload,
            max_events=max_events,
            duration_seconds=duration_seconds,
            event_types=event_types,
        )
    )
    return {"ok": True, "events": events_count}


def _cmd_server_run(args: argparse.Namespace) -> Mapping[str, Any]:
    app_id, app_secret = _resolve_app_credentials(args)
    server = FeishuBotServer(
        app_id=app_id,
        app_secret=app_secret,
        domain=_resolve_open_domain(args),
        timeout_seconds=_resolve_timeout_seconds(args),
    )
    output_file = _resolve_output_path(getattr(args, "output_file", None))
    max_events = _validate_max_events(getattr(args, "max_events", None))
    state: dict[str, Any] = {"events": 0, "stop_requested": False}

    def _on_event(ctx: Any) -> None:
        event = _build_event_view(ctx, include_payload=bool(getattr(args, "print_payload", False)))
        _emit_event(
            event,
            output_format=str(args.output_format),
            output_file=output_file,
        )
        state["events"] = int(state["events"]) + 1
        if max_events is not None and int(state["events"]) >= max_events and not bool(state["stop_requested"]):
            state["stop_requested"] = True
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(server.stop())
            except RuntimeError:
                pass
        return None

    event_types = list(getattr(args, "event_types", []) or [])
    if event_types:
        for event_type in event_types:
            server.on_event(str(event_type), _on_event)
    else:
        server.on_default(_on_event)

    server.run(handle_signals=not bool(getattr(args, "no_handle_signals", False)))
    return {"ok": True, "events": int(state["events"])}


def _cmd_server_start(args: argparse.Namespace) -> Mapping[str, Any]:
    pid_file = _resolve_pid_file(getattr(args, "pid_file", None))
    existing_pid = _read_pid_file(pid_file)
    if existing_pid is not None and _is_process_alive(existing_pid):
        raise ValueError(f"server is already running with pid={existing_pid} ({pid_file})")

    cmd = _build_server_run_subprocess_command(args)
    log_file = getattr(args, "log_file", None)
    process = _spawn_background_process(cmd, log_file=log_file)
    _write_pid_file(pid_file, process.pid)
    return {
        "ok": True,
        "pid": process.pid,
        "pid_file": str(pid_file),
        "log_file": str(log_file) if log_file else None,
    }


def _cmd_server_status(args: argparse.Namespace) -> Mapping[str, Any]:
    pid_file = _resolve_pid_file(getattr(args, "pid_file", None))
    pid = _read_pid_file(pid_file)
    if pid is None:
        return {"running": False, "pid_file": str(pid_file), "pid": None}
    running = _is_process_alive(pid)
    return {"running": running, "pid_file": str(pid_file), "pid": pid}


def _cmd_server_stop(args: argparse.Namespace) -> Mapping[str, Any]:
    pid_file = _resolve_pid_file(getattr(args, "pid_file", None))
    pid = _read_pid_file(pid_file)
    if pid is None:
        return {"ok": False, "stopped": False, "reason": "pid file not found", "pid_file": str(pid_file)}
    if not _is_process_alive(pid):
        _remove_pid_file(pid_file)
        return {"ok": True, "stopped": False, "reason": "process already exited", "pid": pid}

    _terminate_process(pid)
    _remove_pid_file(pid_file)
    return {"ok": True, "stopped": True, "pid": pid, "pid_file": str(pid_file)}


def _serve_webhook_http(
    *,
    receiver: WebhookReceiver,
    host: str,
    port: int,
    path: str,
    output_format: str,
    max_requests: int | None,
) -> None:
    state: dict[str, int] = {"requests": 0}

    class _Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            request_path = self.path.split("?", 1)[0]
            if request_path != path:
                self._send_json(404, {"ok": False, "error": "not found"})
                return

            raw_body = _read_request_body(self.headers, self.rfile)
            headers = {str(k): str(v) for k, v in self.headers.items()}
            try:
                response = receiver.handle(headers, raw_body)
                self._send_json(200, response)
            except Exception as exc:
                error_payload = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
                self._send_json(400, error_payload)
                _print_runtime_error(error_payload["error"], output_format=output_format)
            finally:
                state["requests"] = int(state["requests"]) + 1
                if max_requests is not None and int(state["requests"]) >= max_requests:
                    threading.Thread(target=self.server.shutdown, daemon=True).start()

        def do_GET(self) -> None:  # noqa: N802
            self._send_json(200, {"ok": True, "path": path})

        def log_message(self, format: str, *args: object) -> None:  # noqa: A003
            return

        def _send_json(self, status_code: int, payload: Mapping[str, Any]) -> None:
            body = json.dumps(_to_jsonable(payload), ensure_ascii=False).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    startup_payload = {"status": "listening", "host": host, "port": port, "path": path}
    _print_runtime_status(startup_payload, output_format=output_format)
    with ThreadingHTTPServer((host, port), _Handler) as server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
    _print_runtime_status({"status": "stopped", "requests": int(state["requests"])}, output_format=output_format)


async def _run_ws_listener(
    *,
    app_id: str,
    app_secret: str,
    domain: str,
    timeout_seconds: float,
    output_format: str,
    output_file: Path | None,
    print_payload: bool,
    max_events: int | None,
    duration_seconds: float | None,
    event_types: list[str],
) -> int:
    registry = FeishuEventRegistry()
    state: dict[str, Any] = {"events": 0, "stop_requested": False}
    client: AsyncLongConnectionClient | None = None

    def _request_stop() -> None:
        if client is None:
            return
        if bool(state["stop_requested"]):
            return
        state["stop_requested"] = True
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(client.stop())
        except RuntimeError:
            pass

    def _on_event(ctx: EventContext) -> None:
        event = _build_event_view(ctx, include_payload=print_payload)
        _emit_event(event, output_format=output_format, output_file=output_file)
        state["events"] = int(state["events"]) + 1
        if max_events is not None and int(state["events"]) >= max_events:
            _request_stop()

    if event_types:
        for event_type in event_types:
            registry.register(event_type, _on_event)
    else:
        registry.register_default(_on_event)

    client = AsyncLongConnectionClient(
        app_id=app_id,
        app_secret=app_secret,
        handler_registry=registry,
        domain=domain,
        timeout_seconds=timeout_seconds,
    )

    run_task = asyncio.create_task(client.start())
    try:
        if duration_seconds is not None:
            try:
                await asyncio.wait_for(run_task, timeout=duration_seconds)
            except asyncio.TimeoutError:
                _request_stop()
                try:
                    await asyncio.wait_for(run_task, timeout=max(timeout_seconds, 5.0))
                except asyncio.CancelledError:
                    pass
        else:
            try:
                await run_task
            except asyncio.CancelledError:
                if not bool(state["stop_requested"]):
                    raise
    finally:
        if not run_task.done():
            await client.stop()
            with contextlib.suppress(Exception):
                await run_task
    return int(state["events"])


def _build_client(args: argparse.Namespace) -> FeishuClient:
    return FeishuClient(_build_config(args))


def _build_config(args: argparse.Namespace) -> FeishuConfig:
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
    auth_mode = (env_auth_mode or getattr(args, "auth_mode", None) or "tenant").strip().lower()
    base_url = getattr(args, "base_url", None) or env_base_url or _DEFAULT_BASE_URL
    app_access_token = env_app_access_token or getattr(args, "app_access_token", None)
    user_access_token = env_user_access_token or getattr(args, "user_access_token", None)
    user_refresh_token = env_user_refresh_token or getattr(args, "user_refresh_token", None)
    generic_access_token = env_access_token or getattr(args, "access_token", None)
    resolved_access_token = generic_access_token

    timeout_seconds = _resolve_timeout_seconds(args)

    if auth_mode not in {"tenant", "user"}:
        raise ConfigurationError("invalid auth mode: FEISHU_AUTH_MODE/--auth-mode must be 'tenant' or 'user'")

    if getattr(args, "group", None) == "oauth":
        oauth_command = str(getattr(args, "oauth_command", ""))
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
        )

    if auth_mode == "tenant":
        if not resolved_access_token and (not app_id or not app_secret):
            raise ConfigurationError(
                "tenant mode requires either access_token or app_id/app_secret"
            )
    else:
        if not resolved_access_token:
            resolved_access_token = user_access_token
        if not resolved_access_token and not user_refresh_token:
            raise ConfigurationError(
                "user mode requires user_access_token/access_token or user_refresh_token"
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
    )


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


def _validate_positive_int(value: object, *, name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = int(value)
        except ValueError as exc:
            raise ValueError(f"{name} must be a positive integer") from exc
    else:
        raise ValueError(f"{name} must be a positive integer")
    if parsed <= 0:
        raise ValueError(f"{name} must be greater than 0")
    return parsed


def _validate_max_events(value: object) -> int | None:
    return _validate_positive_int(value, name="max-events")


def _validate_duration(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        parsed = float(value)
    elif isinstance(value, str):
        try:
            parsed = float(value)
        except ValueError as exc:
            raise ValueError("duration-seconds must be a positive number") from exc
    else:
        raise ValueError("duration-seconds must be a positive number")
    if parsed <= 0:
        raise ValueError("duration-seconds must be greater than 0")
    return parsed


def _resolve_output_path(path_value: object) -> Path | None:
    if not path_value:
        return None
    return Path(str(path_value))


def _resolve_pid_file(path_value: object) -> Path:
    if not path_value:
        return Path(".feishu_server.pid")
    return Path(str(path_value))


def _read_pid_file(pid_file: Path) -> int | None:
    if not pid_file.exists():
        return None
    text = pid_file.read_text(encoding="utf-8").strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _write_pid_file(pid_file: Path, pid: int) -> None:
    if pid_file.parent and not pid_file.parent.exists():
        pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(pid), encoding="utf-8")


def _remove_pid_file(pid_file: Path) -> None:
    if pid_file.exists():
        pid_file.unlink()


def _is_process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        completed = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            return False
        output = (completed.stdout or "").strip()
        if not output:
            return False
        if output.startswith("INFO:"):
            return False
        return str(pid) in output
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _terminate_process(pid: int) -> None:
    if os.name == "nt":
        completed = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"failed to stop process pid={pid}: {completed.stderr or completed.stdout}")
        return
    os.kill(pid, signal.SIGTERM)


def _build_server_run_subprocess_command(args: argparse.Namespace) -> list[str]:
    cmd = [
        sys.executable,
        "-m",
        "feishu_bot_sdk",
        "server",
        "run",
        "--format",
        "json",
    ]
    domain = getattr(args, "domain", None)
    if domain:
        cmd.extend(["--domain", str(domain)])
    if bool(getattr(args, "print_payload", False)):
        cmd.append("--print-payload")
    output_file = getattr(args, "output_file", None)
    if output_file:
        cmd.extend(["--output-file", str(output_file)])
    max_events = getattr(args, "max_events", None)
    if max_events is not None:
        cmd.extend(["--max-events", str(max_events)])
    for event_type in list(getattr(args, "event_types", []) or []):
        cmd.extend(["--event-type", str(event_type)])
    return cmd


def _spawn_background_process(cmd: list[str], *, log_file: object) -> subprocess.Popen[Any]:
    stdout_target: Any = subprocess.DEVNULL
    stderr_target: Any = subprocess.DEVNULL
    log_handle: Any = None
    if log_file:
        log_path = Path(str(log_file))
        if log_path.parent and not log_path.parent.exists():
            log_path.parent.mkdir(parents=True, exist_ok=True)
        log_handle = log_path.open("a", encoding="utf-8")
        stdout_target = log_handle
        stderr_target = log_handle

    popen_kwargs: dict[str, Any] = {
        "stdout": stdout_target,
        "stderr": stderr_target,
        "stdin": subprocess.DEVNULL,
        "close_fds": True,
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    else:
        popen_kwargs["start_new_session"] = True
    try:
        return subprocess.Popen(cmd, **popen_kwargs)
    finally:
        if log_handle is not None:
            log_handle.close()


def _normalize_server_path(path: str) -> str:
    if path.startswith("/"):
        return path
    return f"/{path}"


def _resolve_text_input(
    *,
    text: str | None,
    file_path: str | None,
    stdin_enabled: bool = False,
    name: str,
) -> str:
    source_count = int(bool(text)) + int(bool(file_path)) + int(bool(stdin_enabled))
    if source_count != 1:
        raise ValueError(
            f"exactly one of --{name}, --{name}-file or --{name}-stdin is required"
        )
    if text is not None:
        return text
    if file_path is not None:
        return Path(str(file_path)).read_text(encoding="utf-8")
    return _read_stdin_text()


def _parse_json_object(
    *,
    json_text: str | None,
    file_path: str | None,
    stdin_enabled: bool = False,
    name: str,
    required: bool,
) -> dict[str, Any]:
    source_count = int(bool(json_text)) + int(bool(file_path)) + int(bool(stdin_enabled))
    if source_count > 1:
        raise ValueError(
            f"only one of --{name}-json, --{name}-file or --{name}-stdin can be used"
        )
    if source_count == 0:
        if required:
            raise ValueError(
                f"one of --{name}-json, --{name}-file or --{name}-stdin is required"
            )
        return {}

    if json_text is not None:
        raw = json_text
    elif file_path is not None:
        raw = Path(str(file_path)).read_text(encoding="utf-8")
    else:
        raw = _read_stdin_text()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{name} is not valid JSON: {exc}") from exc
    if not isinstance(parsed, Mapping):
        raise ValueError(f"{name} must be a JSON object")
    return {str(key): value for key, value in parsed.items()}


def _parse_json_array(
    *,
    json_text: str | None,
    file_path: str | None,
    stdin_enabled: bool = False,
    name: str,
    required: bool,
) -> list[Any]:
    source_count = int(bool(json_text)) + int(bool(file_path)) + int(bool(stdin_enabled))
    if source_count > 1:
        raise ValueError(
            f"only one of --{name}-json, --{name}-file or --{name}-stdin can be used"
        )
    if source_count == 0:
        if required:
            raise ValueError(
                f"one of --{name}-json, --{name}-file or --{name}-stdin is required"
            )
        return []

    if json_text is not None:
        raw = json_text
    elif file_path is not None:
        raw = Path(str(file_path)).read_text(encoding="utf-8")
    else:
        raw = _read_stdin_text()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{name} is not valid JSON: {exc}") from exc
    if not isinstance(parsed, list):
        raise ValueError(f"{name} must be a JSON array")
    return list(parsed)


def _resolve_raw_body(
    *,
    body_json: str | None,
    body_file: str | None,
    stdin_enabled: bool = False,
) -> bytes:
    source_count = int(bool(body_json)) + int(bool(body_file)) + int(bool(stdin_enabled))
    if source_count > 1:
        raise ValueError("only one of --body-json, --body-file or --body-stdin can be used")
    if source_count == 0:
        raise ValueError("one of --body-json, --body-file or --body-stdin is required")
    if body_json is not None:
        return body_json.encode("utf-8")
    if body_file is not None:
        return Path(str(body_file)).read_bytes()
    return _read_stdin_bytes()


def _read_stdin_text() -> str:
    return sys.stdin.read()


def _read_stdin_bytes() -> bytes:
    stream = getattr(sys.stdin, "buffer", None)
    if stream is None:
        return sys.stdin.read().encode("utf-8")
    data = stream.read()
    if isinstance(data, bytes):
        return data
    return bytes(data)


def _normalize_path(path: str) -> str:
    if path.startswith("/"):
        return path
    return f"/{path}"


def _read_request_body(headers: Any, stream: Any) -> bytes:
    content_length_raw = None
    items = headers.items() if hasattr(headers, "items") else []
    for key, value in items:
        if str(key).lower() == "content-length":
            content_length_raw = value
            break
    if content_length_raw is None:
        return b""
    try:
        content_length = int(str(content_length_raw))
    except ValueError:
        return b""
    if content_length <= 0:
        return b""
    return bytes(stream.read(content_length))


def _print_result(result: Any, *, output_format: str) -> None:
    normalized = _to_jsonable(result)
    if output_format == "json":
        print(json.dumps(normalized, ensure_ascii=False, indent=2))
        return
    _print_human(normalized)


def _print_human(result: Any) -> None:
    if result is None:
        print("OK")
        return
    if isinstance(result, Mapping):
        mapping = {str(key): value for key, value in result.items()}
        if not mapping:
            print("OK")
            return
        if _is_flat_mapping(mapping):
            width = max(len(key) for key in mapping)
            for key in sorted(mapping):
                print(f"{key:<{width}} : {mapping[key]}")
            return
        print(json.dumps(mapping, ensure_ascii=False, indent=2))
        return
    if isinstance(result, list):
        if not result:
            print("[]")
            return
        for index, item in enumerate(result, start=1):
            print(f"{index}. {item}")
        return
    print(result)


def _build_event_view(ctx: Any, *, include_payload: bool) -> Mapping[str, Any]:
    envelope = getattr(ctx, "envelope", None)
    payload = getattr(ctx, "payload", {})
    event = getattr(ctx, "event", {})
    result: dict[str, Any] = {
        "event_type": str(getattr(envelope, "event_type", "")),
        "event_id": getattr(envelope, "event_id", None),
    }
    sender_open_id = _extract_nested_value(
        event,
        ["sender", "sender_id", "open_id"],
    )
    message_id = _extract_nested_value(
        event,
        ["message", "message_id"],
    )
    chat_id = _extract_nested_value(
        event,
        ["message", "chat_id"],
    )
    if isinstance(sender_open_id, str) and sender_open_id:
        result["sender_open_id"] = sender_open_id
    if isinstance(message_id, str) and message_id:
        result["message_id"] = message_id
    if isinstance(chat_id, str) and chat_id:
        result["chat_id"] = chat_id
    if include_payload:
        result["payload"] = payload
    return result


def _extract_nested_value(source: Any, path: list[str]) -> Any:
    current = source
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _emit_event(event: Mapping[str, Any], *, output_format: str, output_file: Path | None) -> None:
    _print_stream_event(event, output_format=output_format)
    if output_file is not None:
        _append_jsonl(output_file, event)


def _print_stream_event(event: Mapping[str, Any], *, output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(_to_jsonable(event), ensure_ascii=False))
        return
    event_type = event.get("event_type")
    event_id = event.get("event_id")
    print(f"[event] type={event_type} id={event_id}")
    if "payload" in event:
        print(json.dumps(_to_jsonable(event.get("payload")), ensure_ascii=False, indent=2))


def _append_jsonl(path: Path, event: Mapping[str, Any]) -> None:
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(_to_jsonable(event), ensure_ascii=False))
        file.write("\n")


def _print_runtime_status(payload: Mapping[str, Any], *, output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(_to_jsonable(payload), ensure_ascii=False))
        return
    status = payload.get("status")
    if status == "listening":
        print(f"Listening on http://{payload.get('host')}:{payload.get('port')}{payload.get('path')}")
        return
    if status == "stopped":
        print(f"Server stopped. requests={payload.get('requests')}")
        return
    print(json.dumps(_to_jsonable(payload), ensure_ascii=False))


def _print_runtime_error(message: str, *, output_format: str) -> None:
    if output_format == "json":
        print(json.dumps({"error": message}, ensure_ascii=False))
    else:
        print(f"Runtime error: {message}", file=sys.stderr)


def _print_error(message: str, *, exit_code: int, output_format: str) -> int:
    if output_format == "json":
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": message,
                    "exit_code": exit_code,
                },
                ensure_ascii=False,
            )
        )
    else:
        print(f"Error: {message}", file=sys.stderr)
    return exit_code


def _format_http_error(exc: HTTPRequestError) -> str:
    parts = [str(exc)]
    if exc.status_code is not None:
        parts.append(f"status_code={exc.status_code}")
    if exc.response_text:
        parts.append(f"response={exc.response_text[:500]}")
        response_lower = exc.response_text.lower()
        if '"code":193107' in response_lower or "no permission to access attachment file token" in response_lower:
            parts.append(
                "hint=calendar attachments require media upload with "
                "parent_type='calendar' and parent_node='<calendar_id>'; "
                "prefer `feishu calendar attach-material`."
            )
    return "; ".join(parts)


def _is_flat_mapping(mapping: Mapping[str, Any]) -> bool:
    for value in mapping.values():
        if isinstance(value, (dict, list, tuple, set)):
            return False
    return True


def _to_jsonable(value: Any) -> Any:
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return _to_jsonable(to_dict())
    if dataclasses.is_dataclass(value):
        return _to_jsonable(dataclasses.asdict(value))
    if isinstance(value, Mapping):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _extract_response_data(value: Any) -> dict[str, Any]:
    payload = _to_jsonable(value)
    if not isinstance(payload, Mapping):
        return {}
    data = payload.get("data")
    if isinstance(data, Mapping):
        return {str(key): inner for key, inner in data.items()}
    return {
        str(key): inner
        for key, inner in payload.items()
        if key not in {"code", "msg"}
    }


def _normalize_calendar_attachments(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    attachments: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        file_token_value = item.get("file_token")
        if not isinstance(file_token_value, str) or not file_token_value:
            continue
        attachment: dict[str, Any] = {"file_token": file_token_value}
        name = item.get("name")
        if isinstance(name, str) and name:
            attachment["name"] = name
        is_deleted = item.get("is_deleted")
        if isinstance(is_deleted, bool):
            attachment["is_deleted"] = is_deleted
        attachments.append(attachment)
    return attachments


def _merge_calendar_attachment(
    attachments: list[dict[str, Any]],
    *,
    file_token: str,
    name: Optional[str],
) -> list[dict[str, Any]]:
    merged = [dict(item) for item in attachments]
    for item in merged:
        if item.get("file_token") != file_token:
            continue
        if isinstance(name, str) and name:
            item["name"] = name
        return merged
    new_item: dict[str, Any] = {"file_token": file_token}
    if isinstance(name, str) and name:
        new_item["name"] = name
    merged.append(new_item)
    return merged


def _system_exit_code(exc: SystemExit) -> int:
    code = exc.code
    if code is None:
        return 0
    if isinstance(code, int):
        return code
    return 1
