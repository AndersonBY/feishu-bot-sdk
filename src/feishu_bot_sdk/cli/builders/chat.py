from __future__ import annotations

import argparse

from ..commands import (
    _cmd_chat_announcement_batch_update,
    _cmd_chat_announcement_create_children,
    _cmd_chat_announcement_delete_children,
    _cmd_chat_announcement_get,
    _cmd_chat_announcement_get_block,
    _cmd_chat_announcement_list_blocks,
    _cmd_chat_announcement_list_children,
    _cmd_chat_create,
    _cmd_chat_delete,
    _cmd_chat_get,
    _cmd_chat_get_link,
    _cmd_chat_list,
    _cmd_chat_manager_add,
    _cmd_chat_manager_remove,
    _cmd_chat_member_add,
    _cmd_chat_member_check,
    _cmd_chat_member_join,
    _cmd_chat_member_list,
    _cmd_chat_member_remove,
    _cmd_chat_menu_create,
    _cmd_chat_menu_delete,
    _cmd_chat_menu_get,
    _cmd_chat_menu_sort,
    _cmd_chat_menu_update_item,
    _cmd_chat_moderation_get,
    _cmd_chat_moderation_update,
    _cmd_chat_search,
    _cmd_chat_tab_create,
    _cmd_chat_tab_delete,
    _cmd_chat_tab_list,
    _cmd_chat_tab_sort,
    _cmd_chat_tab_update,
    _cmd_chat_top_notice_delete,
    _cmd_chat_top_notice_put,
    _cmd_chat_update,
)
from ..settings import HELP_FORMATTER as _HELP_FORMATTER

_USER_ID_TYPE_CHOICES = ("open_id", "user_id", "union_id")
_MEMBER_ID_TYPE_CHOICES = ("open_id", "user_id", "union_id", "app_id")
_BOOL_CHOICES = ("true", "false")
_LINK_VALIDITY_CHOICES = ("week", "year", "permanently")
_MODERATION_SETTING_CHOICES = ("all_members", "only_owner", "moderator_list")
_TOP_NOTICE_ACTION_CHOICES = ("1", "2")


def _add_json_source_args(
    parser: argparse.ArgumentParser,
    *,
    name: str,
    label: str,
    json_help: str | None = None,
) -> None:
    flag_name = name.replace("_", "-")
    parser.add_argument(f"--{flag_name}-json", help=json_help or f"{label} JSON object")
    parser.add_argument(f"--{flag_name}-file", help=f"{label} JSON file path")
    parser.add_argument(f"--{flag_name}-stdin", action="store_true", help=f"Read {label} JSON from stdin")


def _add_json_array_source_args(
    parser: argparse.ArgumentParser,
    *,
    name: str,
    label: str,
    json_help: str | None = None,
) -> None:
    flag_name = name.replace("_", "-")
    parser.add_argument(f"--{flag_name}-json", help=json_help or f"{label} JSON array")
    parser.add_argument(f"--{flag_name}-file", help=f"{label} JSON array file path")
    parser.add_argument(f"--{flag_name}-stdin", action="store_true", help=f"Read {label} JSON array from stdin")


def _add_id_list_args(
    parser: argparse.ArgumentParser,
    *,
    singular_flag: str,
    dest: str,
    label: str,
) -> None:
    parser.add_argument(f"--{singular_flag}", action="append", dest=dest, help=f"{label}, repeatable")
    plural_flag = dest.replace("_", "-")
    parser.add_argument(f"--{plural_flag}-json", help=f"{label} JSON array")
    parser.add_argument(f"--{plural_flag}-file", help=f"{label} JSON array file path")
    parser.add_argument(f"--{plural_flag}-stdin", action="store_true", help=f"Read {label} JSON array from stdin")


def _add_paging_args(parser: argparse.ArgumentParser, *, include_all: bool) -> None:
    parser.add_argument("--page-size", type=int, help="Page size")
    parser.add_argument("--page-token", help="Page token")
    if include_all:
        parser.add_argument("--all", action="store_true", help="Auto paginate and return all items")


def _add_announcement_args(
    parser: argparse.ArgumentParser,
    *,
    include_client_token: bool,
    include_paging: bool,
    include_user_id_type: bool = True,
) -> None:
    parser.add_argument("--revision-id", type=int, help="Optional announcement revision id (-1 = latest)")
    if include_client_token:
        parser.add_argument("--client-token", help="Optional idempotency token")
    if include_user_id_type:
        parser.add_argument("--user-id-type", choices=_USER_ID_TYPE_CHOICES, help="Optional user_id_type")
    if include_paging:
        _add_paging_args(parser, include_all=True)


def _build_chat_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    shared: argparse.ArgumentParser,
) -> None:
    chat_parser = subparsers.add_parser(
        "chat",
        aliases=["group"],
        help="Chat / group operations",
        description=(
            "Manage Feishu group chats from CLI.\n"
            "Covers chat metadata, members, managers, moderation, announcements, chat tabs, and chat menu.\n"
            "Complex write operations accept JSON from --*-json/--*-file/--*-stdin, and most list commands support --all."
        ),
        formatter_class=_HELP_FORMATTER,
        epilog=(
            "Examples:\n"
            "  feishu chat list --all --format json\n"
            "  feishu chat create --chat-json '{\"name\":\"Ops War Room\",\"owner_id\":\"ou_xxx\",\"user_id_list\":[\"ou_xxx\"],\"chat_mode\":\"group\",\"chat_type\":\"private\"}' --user-id-type open_id --format json\n"
            "  feishu chat member add --chat-id oc_xxx --member-id ou_xxx --member-id-type open_id --format json\n"
            "  feishu chat announcement list-blocks --chat-id oc_xxx --all --format json"
        ),
    )
    chat_sub = chat_parser.add_subparsers(dest="chat_command")
    chat_sub.required = True

    create = chat_sub.add_parser(
        "create",
        help="Create a group chat",
        parents=[shared],
        description=(
            "Create a normal group chat.\n"
            "Provide the request body as a JSON object. Common fields: name, description, owner_id, user_id_list, bot_id_list, chat_mode, chat_type."
        ),
        formatter_class=_HELP_FORMATTER,
    )
    _add_json_source_args(
        create,
        name="chat",
        label="Chat body",
        json_help='Chat JSON object, e.g. {"name":"Ops War Room","owner_id":"ou_xxx","user_id_list":["ou_xxx"],"chat_mode":"group","chat_type":"private"}',
    )
    create.add_argument("--user-id-type", choices=_USER_ID_TYPE_CHOICES, help="User ID type used by owner_id and user_id_list")
    create.add_argument("--set-bot-manager", choices=_BOOL_CHOICES, help="Whether to keep the creating bot as manager when owner_id is a user")
    create.add_argument("--uuid", help="Optional idempotency uuid")
    create.set_defaults(handler=_cmd_chat_create)

    get = chat_sub.add_parser("get", help="Get chat details", parents=[shared])
    get.add_argument("--chat-id", required=True, help="Chat id")
    get.add_argument("--user-id-type", choices=_USER_ID_TYPE_CHOICES, help="Optional user_id_type")
    get.set_defaults(handler=_cmd_chat_get)

    list_parser = chat_sub.add_parser(
        "list",
        help="List chats visible to current bot/user",
        parents=[shared],
        description="List chats the current bot or user is in.",
    )
    list_parser.add_argument("--user-id-type", choices=_USER_ID_TYPE_CHOICES, help="Optional user_id_type")
    list_parser.add_argument("--sort-type", help="Optional sort_type from the API")
    _add_paging_args(list_parser, include_all=True)
    list_parser.set_defaults(handler=_cmd_chat_list)

    search = chat_sub.add_parser(
        "search",
        help="Search visible chats",
        parents=[shared],
        description="Search chats visible to the current bot or user by keyword.",
    )
    search.add_argument("--query", required=True, help="Search keyword")
    search.add_argument("--user-id-type", choices=_USER_ID_TYPE_CHOICES, help="Optional user_id_type")
    _add_paging_args(search, include_all=True)
    search.set_defaults(handler=_cmd_chat_search)

    update = chat_sub.add_parser(
        "update",
        help="Update chat details",
        parents=[shared],
        description=(
            "Update chat metadata or settings.\n"
            "Provide a JSON object with the fields you want to change. Typical fields: name, description, owner_id, membership_approval, restricted_mode_setting."
        ),
        formatter_class=_HELP_FORMATTER,
    )
    update.add_argument("--chat-id", required=True, help="Chat id")
    _add_json_source_args(
        update,
        name="chat",
        label="Chat patch body",
        json_help='Chat patch JSON object, e.g. {"name":"Ops War Room","description":"Incident response","membership_approval":"no_approval_required"}',
    )
    update.add_argument("--user-id-type", choices=_USER_ID_TYPE_CHOICES, help="User ID type used by owner_id if present")
    update.set_defaults(handler=_cmd_chat_update)

    delete = chat_sub.add_parser("delete", help="Dissolve a chat", parents=[shared])
    delete.add_argument("--chat-id", required=True, help="Chat id")
    delete.set_defaults(handler=_cmd_chat_delete)

    get_link = chat_sub.add_parser(
        "get-link",
        help="Create or fetch a share link for a chat",
        parents=[shared],
        description="Create a share link for a chat. Works only for supported group chats, not p2p/secret/team chats.",
    )
    get_link.add_argument("--chat-id", required=True, help="Chat id")
    get_link.add_argument("--validity-period", choices=_LINK_VALIDITY_CHOICES, help="Link validity: week, year, or permanently")
    get_link.set_defaults(handler=_cmd_chat_get_link)

    moderation = chat_sub.add_parser("moderation", help="Chat speaking-permission operations")
    moderation_sub = moderation.add_subparsers(dest="chat_moderation_command")
    moderation_sub.required = True

    moderation_get = moderation_sub.add_parser(
        "get",
        help="Get speaking permissions",
        parents=[shared],
        description="Get the speaking mode and allowed speakers for a chat.",
    )
    moderation_get.add_argument("--chat-id", required=True, help="Chat id")
    moderation_get.add_argument("--user-id-type", choices=_USER_ID_TYPE_CHOICES, help="Optional user_id_type")
    _add_paging_args(moderation_get, include_all=True)
    moderation_get.set_defaults(handler=_cmd_chat_moderation_get)

    moderation_update = moderation_sub.add_parser(
        "update",
        help="Update speaking permissions",
        parents=[shared],
        description=(
            "Update chat speaking permissions.\n"
            "Either pass the full request object via --moderation-json/... or use --moderation-setting plus optional moderator add/remove ids."
        ),
        formatter_class=_HELP_FORMATTER,
    )
    moderation_update.add_argument("--chat-id", required=True, help="Chat id")
    _add_json_source_args(
        moderation_update,
        name="moderation",
        label="Moderation body",
        json_help='Moderation JSON object, e.g. {"moderation_setting":"moderator_list","moderator_added_list":["ou_xxx"],"moderator_removed_list":["ou_yyy"]}',
    )
    moderation_update.add_argument("--user-id-type", choices=_USER_ID_TYPE_CHOICES, help="User ID type for moderator ids")
    moderation_update.add_argument("--moderation-setting", choices=_MODERATION_SETTING_CHOICES, help="Speaking mode")
    _add_id_list_args(moderation_update, singular_flag="moderator-added-id", dest="moderator_added_ids", label="Moderator ID to add")
    _add_id_list_args(moderation_update, singular_flag="moderator-removed-id", dest="moderator_removed_ids", label="Moderator ID to remove")
    moderation_update.set_defaults(handler=_cmd_chat_moderation_update)

    top_notice = chat_sub.add_parser("top-notice", help="Pinned top-notice operations")
    top_notice_sub = top_notice.add_subparsers(dest="chat_top_notice_command")
    top_notice_sub.required = True

    top_notice_put = top_notice_sub.add_parser(
        "put",
        help="Set top notice",
        parents=[shared],
        description=(
            "Pin either a message or the chat announcement as top notice.\n"
            "Either pass the full request object via --top-notice-json/... or use --action-type and optional --message-id."
        ),
        formatter_class=_HELP_FORMATTER,
    )
    top_notice_put.add_argument("--chat-id", required=True, help="Chat id")
    _add_json_source_args(
        top_notice_put,
        name="top_notice",
        label="Top notice body",
        json_help='Top notice JSON object, e.g. {"chat_top_notice":[{"action_type":"1","message_id":"om_xxx"}]}',
    )
    top_notice_put.add_argument("--action-type", choices=_TOP_NOTICE_ACTION_CHOICES, help="1 = pin a message, 2 = pin the announcement")
    top_notice_put.add_argument("--message-id", help="Message id to pin when action_type=1")
    top_notice_put.set_defaults(handler=_cmd_chat_top_notice_put)

    top_notice_delete = top_notice_sub.add_parser("delete", help="Clear top notice", parents=[shared])
    top_notice_delete.add_argument("--chat-id", required=True, help="Chat id")
    top_notice_delete.set_defaults(handler=_cmd_chat_top_notice_delete)

    member = chat_sub.add_parser("member", help="Chat member operations")
    member_sub = member.add_subparsers(dest="chat_member_command")
    member_sub.required = True

    member_add = member_sub.add_parser(
        "add",
        help="Add users or bots to a chat",
        parents=[shared],
        description="Add users or bots to a chat. Use repeated --member-id flags or provide a JSON array.",
    )
    member_add.add_argument("--chat-id", required=True, help="Chat id")
    member_add.add_argument("--member-id-type", choices=_MEMBER_ID_TYPE_CHOICES, help="ID type for member ids; use app_id for bots")
    member_add.add_argument("--succeed-type", type=int, choices=(0, 1), help="0 = fail on invalid ids, 1 = partial success")
    _add_id_list_args(member_add, singular_flag="member-id", dest="member_ids", label="Member ID")
    member_add.set_defaults(handler=_cmd_chat_member_add)

    member_remove = member_sub.add_parser(
        "remove",
        help="Remove users or bots from a chat",
        parents=[shared],
        description="Remove users or bots from a chat. Use repeated --member-id flags or provide a JSON array.",
    )
    member_remove.add_argument("--chat-id", required=True, help="Chat id")
    member_remove.add_argument("--member-id-type", choices=_MEMBER_ID_TYPE_CHOICES, help="ID type for member ids; use app_id for bots")
    _add_id_list_args(member_remove, singular_flag="member-id", dest="member_ids", label="Member ID")
    member_remove.set_defaults(handler=_cmd_chat_member_remove)

    member_join = member_sub.add_parser("join", help="Join chat as current user/bot", parents=[shared])
    member_join.add_argument("--chat-id", required=True, help="Chat id")
    member_join.set_defaults(handler=_cmd_chat_member_join)

    member_list = member_sub.add_parser(
        "list",
        help="List chat members",
        parents=[shared],
        description="List members in a chat.",
    )
    member_list.add_argument("--chat-id", required=True, help="Chat id")
    member_list.add_argument("--member-id-type", choices=_USER_ID_TYPE_CHOICES, help="Member ID type in the response")
    _add_paging_args(member_list, include_all=True)
    member_list.set_defaults(handler=_cmd_chat_member_list)

    member_check = member_sub.add_parser("check", help="Check whether current user/bot is in chat", parents=[shared])
    member_check.add_argument("--chat-id", required=True, help="Chat id")
    member_check.set_defaults(handler=_cmd_chat_member_check)

    manager = chat_sub.add_parser("manager", help="Chat manager operations")
    manager_sub = manager.add_subparsers(dest="chat_manager_command")
    manager_sub.required = True

    manager_add = manager_sub.add_parser("add", help="Promote managers", parents=[shared])
    manager_add.add_argument("--chat-id", required=True, help="Chat id")
    manager_add.add_argument("--member-id-type", choices=_MEMBER_ID_TYPE_CHOICES, help="ID type for manager ids; use app_id for bots")
    _add_id_list_args(manager_add, singular_flag="manager-id", dest="manager_ids", label="Manager ID")
    manager_add.set_defaults(handler=_cmd_chat_manager_add)

    manager_remove = manager_sub.add_parser("remove", help="Demote managers", parents=[shared])
    manager_remove.add_argument("--chat-id", required=True, help="Chat id")
    manager_remove.add_argument("--member-id-type", choices=_MEMBER_ID_TYPE_CHOICES, help="ID type for manager ids; use app_id for bots")
    _add_id_list_args(manager_remove, singular_flag="manager-id", dest="manager_ids", label="Manager ID")
    manager_remove.set_defaults(handler=_cmd_chat_manager_remove)

    announcement = chat_sub.add_parser(
        "announcement",
        help="Block-based announcement operations",
        description=(
            "Manage the current block-based group announcement under docx/v1/chats/:chat_id/announcement.\n"
            "Use get to inspect metadata and announcement type, then operate on blocks via list/get/create/update/delete subcommands."
        ),
        formatter_class=_HELP_FORMATTER,
    )
    announcement_sub = announcement.add_subparsers(dest="chat_announcement_command")
    announcement_sub.required = True

    announcement_get = announcement_sub.add_parser(
        "get",
        help="Get announcement metadata",
        parents=[shared],
        description="Get announcement metadata, including announcement_type and revision_id.",
    )
    announcement_get.add_argument("--chat-id", required=True, help="Chat id")
    announcement_get.add_argument("--user-id-type", choices=_USER_ID_TYPE_CHOICES, help="Optional user_id_type")
    announcement_get.set_defaults(handler=_cmd_chat_announcement_get)

    announcement_list_blocks = announcement_sub.add_parser(
        "list-blocks",
        help="List all announcement blocks",
        parents=[shared],
        description="List all blocks in the announcement.",
    )
    announcement_list_blocks.add_argument("--chat-id", required=True, help="Chat id")
    _add_announcement_args(announcement_list_blocks, include_client_token=False, include_paging=True)
    announcement_list_blocks.set_defaults(handler=_cmd_chat_announcement_list_blocks)

    announcement_get_block = announcement_sub.add_parser("get-block", help="Get one block", parents=[shared])
    announcement_get_block.add_argument("--chat-id", required=True, help="Chat id")
    announcement_get_block.add_argument("--block-id", required=True, help="Block id")
    _add_announcement_args(announcement_get_block, include_client_token=False, include_paging=False)
    announcement_get_block.set_defaults(handler=_cmd_chat_announcement_get_block)

    announcement_list_children = announcement_sub.add_parser(
        "list-children",
        help="List all child blocks for a parent block",
        parents=[shared],
        description="List child blocks under a parent block in the announcement.",
    )
    announcement_list_children.add_argument("--chat-id", required=True, help="Chat id")
    announcement_list_children.add_argument("--block-id", required=True, help="Parent block id")
    _add_announcement_args(announcement_list_children, include_client_token=False, include_paging=True)
    announcement_list_children.set_defaults(handler=_cmd_chat_announcement_list_children)

    announcement_create_children = announcement_sub.add_parser(
        "create-children",
        help="Create child blocks",
        parents=[shared],
        description=(
            "Create child blocks under a parent block.\n"
            "Provide a JSON array of block objects via --children-json/--children-file/--children-stdin."
        ),
        formatter_class=_HELP_FORMATTER,
    )
    announcement_create_children.add_argument("--chat-id", required=True, help="Chat id")
    announcement_create_children.add_argument("--block-id", required=True, help="Parent block id")
    _add_json_array_source_args(
        announcement_create_children,
        name="children",
        label="Children",
        json_help='Children JSON array, e.g. [{"block_type":2,"text":{"elements":[{"text_run":{"content":"Hello"}}]}}]',
    )
    _add_announcement_args(announcement_create_children, include_client_token=True, include_paging=False)
    announcement_create_children.set_defaults(handler=_cmd_chat_announcement_create_children)

    announcement_batch_update = announcement_sub.add_parser(
        "batch-update",
        help="Batch update blocks",
        parents=[shared],
        description=(
            "Batch update blocks in the announcement.\n"
            "Either provide the full request object via --update-json/... or provide a JSON array of request objects via --requests-json/..."
        ),
        formatter_class=_HELP_FORMATTER,
    )
    announcement_batch_update.add_argument("--chat-id", required=True, help="Chat id")
    _add_json_source_args(
        announcement_batch_update,
        name="update",
        label="Batch update body",
        json_help='Full batch update JSON object, e.g. {"requests":[{"update_text_elements":{"block_id":"doxxx","elements":[...]}}]}',
    )
    _add_json_array_source_args(
        announcement_batch_update,
        name="requests",
        label="Batch update requests",
        json_help='Batch update request JSON array, e.g. [{"update_text_elements":{"block_id":"doxxx","elements":[...]}}]',
    )
    _add_announcement_args(announcement_batch_update, include_client_token=True, include_paging=False)
    announcement_batch_update.set_defaults(handler=_cmd_chat_announcement_batch_update)

    announcement_delete_children = announcement_sub.add_parser(
        "delete-children",
        help="Delete a range of child blocks",
        parents=[shared],
        description=(
            "Delete a range of child blocks under a parent block.\n"
            "Either provide the delete-range object via --delete-range-json/... or use --start-index and --end-index."
        ),
        formatter_class=_HELP_FORMATTER,
    )
    announcement_delete_children.add_argument("--chat-id", required=True, help="Chat id")
    announcement_delete_children.add_argument("--block-id", required=True, help="Parent block id")
    _add_json_source_args(
        announcement_delete_children,
        name="delete_range",
        label="Delete range",
        json_help='Delete range JSON object, e.g. {"start_index":0,"end_index":1}',
    )
    announcement_delete_children.add_argument("--start-index", type=int, help="Start child index (inclusive)")
    announcement_delete_children.add_argument("--end-index", type=int, help="End child index (inclusive)")
    announcement_delete_children.add_argument("--revision-id", type=int, help="Optional announcement revision id (-1 = latest)")
    announcement_delete_children.add_argument("--client-token", help="Optional idempotency token")
    announcement_delete_children.set_defaults(handler=_cmd_chat_announcement_delete_children)

    tab = chat_sub.add_parser("tab", help="Chat tab operations")
    tab_sub = tab.add_subparsers(dest="chat_tab_command")
    tab_sub.required = True

    tab_create = tab_sub.add_parser(
        "create",
        help="Create chat tabs",
        parents=[shared],
        description="Create chat tabs. Provide a JSON array that matches the chat_tabs field.",
    )
    tab_create.add_argument("--chat-id", required=True, help="Chat id")
    _add_json_array_source_args(
        tab_create,
        name="chat_tabs",
        label="Chat tabs",
        json_help='Chat tabs JSON array, e.g. [{"tab_name":"Docs","tab_type":"link","tab_content":{"link":{"url":"https://open.feishu.cn"}}}]',
    )
    tab_create.set_defaults(handler=_cmd_chat_tab_create)

    tab_update = tab_sub.add_parser(
        "update",
        help="Update chat tabs",
        parents=[shared],
        description="Update chat tabs. Provide a JSON array that matches the chat_tabs field and includes tab_id values.",
    )
    tab_update.add_argument("--chat-id", required=True, help="Chat id")
    _add_json_array_source_args(
        tab_update,
        name="chat_tabs",
        label="Chat tabs",
        json_help='Chat tabs JSON array, e.g. [{"tab_id":"7101214603622940671","tab_name":"Docs"}]',
    )
    tab_update.set_defaults(handler=_cmd_chat_tab_update)

    tab_sort = tab_sub.add_parser(
        "sort",
        help="Sort chat tabs",
        parents=[shared],
        description="Sort chat tabs by tab id order. Include the message tab id as the first entry when the API requires it.",
    )
    tab_sort.add_argument("--chat-id", required=True, help="Chat id")
    _add_id_list_args(tab_sort, singular_flag="tab-id", dest="tab_ids", label="Tab ID")
    tab_sort.set_defaults(handler=_cmd_chat_tab_sort)

    tab_list = tab_sub.add_parser("list", help="List chat tabs", parents=[shared])
    tab_list.add_argument("--chat-id", required=True, help="Chat id")
    tab_list.set_defaults(handler=_cmd_chat_tab_list)

    tab_delete = tab_sub.add_parser("delete", help="Delete chat tabs", parents=[shared])
    tab_delete.add_argument("--chat-id", required=True, help="Chat id")
    _add_id_list_args(tab_delete, singular_flag="tab-id", dest="tab_ids", label="Tab ID")
    tab_delete.set_defaults(handler=_cmd_chat_tab_delete)

    menu = chat_sub.add_parser("menu", help="Chat menu operations")
    menu_sub = menu.add_subparsers(dest="chat_menu_command")
    menu_sub.required = True

    menu_create = menu_sub.add_parser(
        "create",
        help="Create chat menu",
        parents=[shared],
        description="Create one or more top-level chat menu items by providing the menu_tree object.",
    )
    menu_create.add_argument("--chat-id", required=True, help="Chat id")
    _add_json_source_args(
        menu_create,
        name="menu_tree",
        label="Menu tree",
        json_help='Menu tree JSON object, e.g. {"chat_menu_top_levels":[{"chat_menu_item":{"name":"Open Feishu","action_type":"REDIRECT_LINK","redirect_link":{"common_url":"https://open.feishu.cn"}}}]}',
    )
    menu_create.set_defaults(handler=_cmd_chat_menu_create)

    menu_get = menu_sub.add_parser("get", help="Get chat menu", parents=[shared])
    menu_get.add_argument("--chat-id", required=True, help="Chat id")
    menu_get.set_defaults(handler=_cmd_chat_menu_get)

    menu_update_item = menu_sub.add_parser(
        "update-item",
        help="Update one menu item",
        parents=[shared],
        description=(
            "Update a single top-level or second-level menu item.\n"
            "Either pass the full update request via --menu-update-json/... or use --menu-item-json with one or more --update-field flags."
        ),
        formatter_class=_HELP_FORMATTER,
    )
    menu_update_item.add_argument("--chat-id", required=True, help="Chat id")
    menu_update_item.add_argument("--menu-item-id", required=True, help="Menu item id")
    _add_json_source_args(
        menu_update_item,
        name="menu_update",
        label="Menu update body",
        json_help='Full menu update JSON object, e.g. {"update_fields":["NAME"],"chat_menu_item":{"name":"Docs"}}',
    )
    _add_json_source_args(
        menu_update_item,
        name="menu_item",
        label="Menu item",
        json_help='Menu item JSON object, e.g. {"name":"Docs","action_type":"REDIRECT_LINK","redirect_link":{"common_url":"https://open.feishu.cn"}}',
    )
    menu_update_item.add_argument("--update-field", action="append", dest="update_fields", help="Field to update, repeatable")
    menu_update_item.set_defaults(handler=_cmd_chat_menu_update_item)

    menu_sort = menu_sub.add_parser("sort", help="Sort top-level menu items", parents=[shared])
    menu_sort.add_argument("--chat-id", required=True, help="Chat id")
    _add_id_list_args(menu_sort, singular_flag="top-level-id", dest="top_level_ids", label="Top-level menu id")
    menu_sort.set_defaults(handler=_cmd_chat_menu_sort)

    menu_delete = menu_sub.add_parser("delete", help="Delete top-level menu items", parents=[shared])
    menu_delete.add_argument("--chat-id", required=True, help="Chat id")
    _add_id_list_args(menu_delete, singular_flag="top-level-id", dest="top_level_ids", label="Top-level menu id")
    menu_delete.set_defaults(handler=_cmd_chat_menu_delete)


__all__ = ["_build_chat_commands"]
