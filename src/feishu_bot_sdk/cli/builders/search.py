from __future__ import annotations

import argparse

from ..commands import _cmd_search_app, _cmd_search_doc_wiki, _cmd_search_message
from ..settings import HELP_FORMATTER as _HELP_FORMATTER


def _build_search_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    shared: argparse.ArgumentParser,
) -> None:
    search_parser = subparsers.add_parser(
        "search",
        help="Search APIs (docs/wiki/apps/messages)",
        description=(
            "Search APIs for docs/wiki, apps, and messages.\n"
            "Most search APIs require user auth mode and related search scopes.\n"
            "Default auth mode for this command group is user."
        ),
        formatter_class=_HELP_FORMATTER,
        epilog=(
            "Examples:\n"
            "  feishu search app --query \"my app\" --all --format json\n"
            "  feishu search message --query \"incident\" --chat-type group_chat --all --format json\n"
            "  feishu search doc-wiki --query \"weekly\" --doc-filter-json '{\"only_title\":true}' --all --format json\n"
            "\n"
            "Scopes (official): search:app / search:message / search:docs:read\n"
            "Override auth mode only if needed: --auth-mode tenant"
        ),
    )
    search_parser.set_defaults(auth_mode="user")
    search_sub = search_parser.add_subparsers(dest="search_command")
    search_sub.required = True

    app = search_sub.add_parser("app", help="Search visible apps", parents=[shared])
    app.add_argument("--query", required=True, help="Search query")
    app.add_argument("--user-id-type", choices=("open_id", "union_id", "user_id"), help="Optional user_id_type")
    app.add_argument("--page-size", type=int, help="Page size")
    app.add_argument("--page-token", help="Page token")
    app.add_argument("--all", action="store_true", help="Auto paginate and return all items")
    app.set_defaults(handler=_cmd_search_app)

    message = search_sub.add_parser("message", help="Search visible messages", parents=[shared])
    message.add_argument("--query", required=True, help="Search query")
    message.add_argument(
        "--user-id-type",
        choices=("open_id", "union_id", "user_id"),
        help="Optional user_id_type",
    )
    message.add_argument("--page-size", type=int, help="Page size")
    message.add_argument("--page-token", help="Page token")
    message.add_argument("--from-id", action="append", dest="from_ids", help="Sender user id, repeatable")
    message.add_argument("--chat-id", action="append", dest="chat_ids", help="Chat id, repeatable")
    message.add_argument("--message-type", choices=("file", "image", "media"), help="Message type filter")
    message.add_argument(
        "--at-chatter-id",
        action="append",
        dest="at_chatter_ids",
        help="Mentioned user id, repeatable",
    )
    message.add_argument("--from-type", choices=("bot", "user"), help="Sender type")
    message.add_argument("--chat-type", choices=("group_chat", "p2p_chat"), help="Chat type")
    message.add_argument("--start-time", help="Message start time (unix seconds string)")
    message.add_argument("--end-time", help="Message end time (unix seconds string)")
    message.add_argument("--all", action="store_true", help="Auto paginate and return all items")
    message.set_defaults(handler=_cmd_search_message)

    doc_wiki = search_sub.add_parser("doc-wiki", help="Search docs and wiki", parents=[shared])
    doc_wiki.add_argument("--query", required=True, help="Search query")
    doc_wiki.add_argument("--doc-filter-json", help='Doc filter JSON, e.g. {"search_obj_type":"doc","doc_type":"docx","only_title":true}')
    doc_wiki.add_argument("--doc-filter-file", help="Doc filter JSON file path")
    doc_wiki.add_argument("--doc-filter-stdin", action="store_true", help="Read doc filter JSON from stdin")
    doc_wiki.add_argument("--wiki-filter-json", help='Wiki filter JSON, e.g. {"space_id":"spc_xxx"}')
    doc_wiki.add_argument("--wiki-filter-file", help="Wiki filter JSON file path")
    doc_wiki.add_argument("--wiki-filter-stdin", action="store_true", help="Read wiki filter JSON from stdin")
    doc_wiki.add_argument("--page-size", type=int, help="Page size")
    doc_wiki.add_argument("--page-token", help="Page token")
    doc_wiki.add_argument("--all", action="store_true", help="Auto paginate and return all res_units")
    doc_wiki.set_defaults(handler=_cmd_search_doc_wiki)


__all__ = ["_build_search_commands"]
