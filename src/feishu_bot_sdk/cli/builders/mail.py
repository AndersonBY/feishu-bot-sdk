from __future__ import annotations

import argparse

from .. import commands as _commands
from ..settings import HELP_FORMATTER as _HELP_FORMATTER

_USER_ID_TYPE_CHOICES = ("open_id", "user_id", "union_id")
_DEPARTMENT_ID_TYPE_CHOICES = ("department_id", "open_department_id")


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


def _add_text_source_args(
    parser: argparse.ArgumentParser,
    *,
    name: str,
    label: str,
) -> None:
    flag_name = name.replace("_", "-")
    parser.add_argument(f"--{flag_name}", help=f"{label} text")
    parser.add_argument(f"--{flag_name}-file", help=f"{label} file path")
    parser.add_argument(f"--{flag_name}-stdin", action="store_true", help=f"Read {label} text from stdin")


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


def _add_user_identity_args(
    parser: argparse.ArgumentParser,
    *,
    include_department: bool,
) -> None:
    parser.add_argument("--user-id-type", choices=_USER_ID_TYPE_CHOICES, help="Optional user_id_type")
    if include_department:
        parser.add_argument(
            "--department-id-type",
            choices=_DEPARTMENT_ID_TYPE_CHOICES,
            help="Optional department_id_type",
        )


def _build_mail_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    shared: argparse.ArgumentParser,
) -> None:
    mail_parser = subparsers.add_parser(
        "mail",
        help="Mail / mailbox / mailing group operations",
        description=(
            "Feishu mail operations for user mailboxes, mail groups, and public mailboxes.\n"
            "Write commands accept JSON from --*-json/--*-file/--*-stdin, and many simple commands also expose direct flags "
            "such as --email-alias, --transfer-mailbox, and --to-mail-address. Paged list commands support --all."
        ),
        formatter_class=_HELP_FORMATTER,
        epilog=(
            "Examples:\n"
            "  feishu mail address query-status --email ops@example.com --email alerts@example.com --format json\n"
            "  feishu mail message list --user-mailbox-id me --folder-id INBOX --all --format json\n"
            "  feishu mail message send-markdown --user-mailbox-id me --to-email user@example.com --subject Daily --markdown-file report.md --format json\n"
            "  feishu mail mailbox alias create --user-mailbox-id me --email-alias alias@example.com --format json\n"
            "  feishu mail group create --mailgroup-json '{\"email\":\"ops@example.com\",\"name\":\"Ops Group\"}' --format json\n"
            "  feishu mail public-mailbox member batch-create --public-mailbox-id support@example.com --items-file members.json --format json"
        ),
    )
    mail_sub = mail_parser.add_subparsers(dest="mail_command")
    mail_sub.required = True

    address = mail_sub.add_parser("address", help="Mail address lookup operations")
    address_sub = address.add_subparsers(dest="mail_address_command")
    address_sub.required = True

    address_query = address_sub.add_parser(
        "query-status",
        help="Query mailbox address status and type",
        parents=[shared],
        description="Query whether each mailbox address exists, its current status, and its mail object type.",
    )
    _add_id_list_args(address_query, singular_flag="email", dest="email_list", label="Email address")
    address_query.set_defaults(handler=_commands._cmd_address_query_status)

    mailbox = mail_sub.add_parser("mailbox", help="User mailbox operations")
    mailbox_sub = mailbox.add_subparsers(dest="mail_mailbox_command")
    mailbox_sub.required = True

    mailbox_alias = mailbox_sub.add_parser("alias", help="User mailbox alias operations")
    mailbox_alias_sub = mailbox_alias.add_subparsers(dest="mail_mailbox_alias_command")
    mailbox_alias_sub.required = True

    mailbox_alias_list = mailbox_alias_sub.add_parser("list", help="List mailbox aliases", parents=[shared])
    mailbox_alias_list.add_argument("--user-mailbox-id", required=True, help='Mailbox id or "me"')
    mailbox_alias_list.set_defaults(handler=_commands._cmd_mailbox_alias_list)

    mailbox_alias_create = mailbox_alias_sub.add_parser("create", help="Create mailbox alias", parents=[shared])
    mailbox_alias_create.add_argument("--user-mailbox-id", required=True, help='Mailbox id or "me"')
    mailbox_alias_create.add_argument("--email-alias", help="Alias email address, maps to request field email_alias")
    _add_json_source_args(
        mailbox_alias_create,
        name="alias",
        label="Alias body",
        json_help='Alias JSON object, e.g. {"email_alias":"alias@example.com"}',
    )
    mailbox_alias_create.set_defaults(handler=_commands._cmd_mailbox_alias_create)

    mailbox_alias_delete = mailbox_alias_sub.add_parser("delete", help="Delete mailbox alias", parents=[shared])
    mailbox_alias_delete.add_argument("--user-mailbox-id", required=True, help='Mailbox id or "me"')
    mailbox_alias_delete.add_argument("--alias-id", required=True, help="Alias id")
    mailbox_alias_delete.set_defaults(handler=_commands._cmd_mailbox_alias_delete)

    mailbox_delete = mailbox_sub.add_parser(
        "delete-from-recycle-bin",
        help="Permanently delete mailbox from recycle bin",
        parents=[shared],
    )
    mailbox_delete.add_argument("--user-mailbox-id", required=True, help="Mailbox id in recycle bin")
    mailbox_delete.add_argument("--transfer-mailbox", help="Optional mailbox that receives transferred mail before deletion")
    mailbox_delete.set_defaults(handler=_commands._cmd_mailbox_delete_from_recycle_bin)

    message = mail_sub.add_parser("message", help="User mailbox message operations")
    message_sub = message.add_subparsers(dest="mail_message_command")
    message_sub.required = True

    message_list = message_sub.add_parser("list", help="List messages in a folder", parents=[shared])
    message_list.add_argument("--user-mailbox-id", required=True, help='Mailbox id or "me"')
    message_list.add_argument("--folder-id", required=True, help="Folder id, e.g. INBOX")
    message_list.add_argument("--only-unread", action="store_true", help="Return unread messages only")
    _add_paging_args(message_list, include_all=True)
    message_list.set_defaults(handler=_commands._cmd_message_list)

    message_get = message_sub.add_parser("get", help="Get message details", parents=[shared])
    message_get.add_argument("--user-mailbox-id", required=True, help='Mailbox id or "me"')
    message_get.add_argument("--message-id", required=True, help="Message id")
    message_get.set_defaults(handler=_commands._cmd_message_get)

    message_get_by_card = message_sub.add_parser("get-by-card", help="Get message by card id", parents=[shared])
    message_get_by_card.add_argument("--user-mailbox-id", required=True, help='Mailbox id or "me"')
    message_get_by_card.add_argument("--card-id", required=True, help="Card id")
    message_get_by_card.add_argument("--owner-id", required=True, help="Owner user id")
    message_get_by_card.add_argument("--user-id-type", choices=_USER_ID_TYPE_CHOICES, help="Optional owner user_id_type")
    message_get_by_card.set_defaults(handler=_commands._cmd_message_get_by_card)

    message_send = message_sub.add_parser("send", help="Send one message", parents=[shared])
    message_send.add_argument("--user-mailbox-id", required=True, help='Mailbox id or "me"')
    _add_json_source_args(
        message_send,
        name="message",
        label="Message body",
        json_help='Message JSON object, e.g. {"subject":"Hello","to":[{"mail_address":"user@example.com"}],"body_html":"<p>Hi</p>"}',
    )
    message_send.set_defaults(handler=_commands._cmd_message_send)

    message_send_markdown = message_sub.add_parser(
        "send-markdown",
        help="Render Markdown to HTML/plain text and send the message",
        parents=[shared],
        description=(
            "Render Markdown into email-safe HTML plus plain-text fallback, inline local paths or "
            "remote image URLs as CID attachments, and send the email. Use --to-email for the simple path, or "
            "--to-json/--cc-json/--bcc-json when you need recipient objects with names."
        ),
        epilog=(
            "Examples:\n"
            "  feishu mail message send-markdown --user-mailbox-id me --to-email user@example.com --subject Daily --markdown-file report.md --format json\n"
            "  feishu mail message send-markdown --user-mailbox-id me --to-json '[{\"mail_address\":\"user@example.com\",\"name\":\"Alex\"}]' --markdown '# Hello' --format json\n"
            "  Relative image paths inside Markdown are resolved from --markdown-file automatically, or from --base-dir if provided.\n"
            "  Remote image URLs in Markdown are fetched automatically and sent as inline CID attachments when reachable."
        ),
    )
    message_send_markdown.add_argument("--user-mailbox-id", required=True, help='Mailbox id or "me"')
    message_send_markdown.add_argument("--subject", help="Optional email subject")
    message_send_markdown.add_argument("--to-email", action="append", dest="to_emails", help="To recipient email, repeatable")
    _add_json_array_source_args(
        message_send_markdown,
        name="to",
        label="To recipients",
        json_help='To recipients JSON array of strings or objects, e.g. ["user@example.com"] or [{"mail_address":"user@example.com","name":"Alex"}]',
    )
    message_send_markdown.add_argument("--cc-email", action="append", dest="cc_emails", help="Cc recipient email, repeatable")
    _add_json_array_source_args(
        message_send_markdown,
        name="cc",
        label="Cc recipients",
        json_help='Cc recipients JSON array of strings or objects, e.g. ["cc@example.com"]',
    )
    message_send_markdown.add_argument("--bcc-email", action="append", dest="bcc_emails", help="Bcc recipient email, repeatable")
    _add_json_array_source_args(
        message_send_markdown,
        name="bcc",
        label="Bcc recipients",
        json_help='Bcc recipients JSON array of strings or objects, e.g. ["audit@example.com"]',
    )
    _add_text_source_args(message_send_markdown, name="markdown", label="Markdown body")
    message_send_markdown.add_argument(
        "--base-dir",
        help="Base directory for resolving relative local image paths inside Markdown",
    )
    message_send_markdown.add_argument(
        "--latex-mode",
        choices=("auto", "mathml", "image", "raw"),
        default="auto",
        help="LaTeX rendering mode. Default: auto",
    )
    message_send_markdown.add_argument("--dedupe-key", help="Optional dedupe_key for idempotent send")
    message_send_markdown.add_argument("--head-from-name", help="Optional head_from.name")
    message_send_markdown.set_defaults(handler=_commands._cmd_message_send_markdown)

    message_attachment = message_sub.add_parser("attachment-download-url", help="Get attachment download URLs", parents=[shared])
    message_attachment.add_argument("--user-mailbox-id", required=True, help='Mailbox id or "me"')
    message_attachment.add_argument("--message-id", required=True, help="Message id")
    _add_id_list_args(message_attachment, singular_flag="attachment-id", dest="attachment_ids", label="Attachment id")
    message_attachment.set_defaults(handler=_commands._cmd_message_attachment_download_url)

    folder = mail_sub.add_parser("folder", help="Mailbox folder operations")
    folder_sub = folder.add_subparsers(dest="mail_folder_command")
    folder_sub.required = True

    folder_list = folder_sub.add_parser("list", help="List folders", parents=[shared])
    folder_list.add_argument("--user-mailbox-id", required=True, help='Mailbox id or "me"')
    folder_list.add_argument(
        "--folder-type",
        type=int,
        choices=(1, 2),
        help="Optional folder type filter: 1 system folder, 2 user folder",
    )
    folder_list.set_defaults(handler=_commands._cmd_folder_list)

    folder_create = folder_sub.add_parser("create", help="Create folder", parents=[shared])
    folder_create.add_argument("--user-mailbox-id", required=True, help='Mailbox id or "me"')
    _add_json_source_args(folder_create, name="folder", label="Folder body")
    folder_create.set_defaults(handler=_commands._cmd_folder_create)

    folder_update = folder_sub.add_parser("update", help="Update folder", parents=[shared])
    folder_update.add_argument("--user-mailbox-id", required=True, help='Mailbox id or "me"')
    folder_update.add_argument("--folder-id", required=True, help="Folder id")
    _add_json_source_args(folder_update, name="folder", label="Folder patch body")
    folder_update.set_defaults(handler=_commands._cmd_folder_update)

    folder_delete = folder_sub.add_parser("delete", help="Delete folder", parents=[shared])
    folder_delete.add_argument("--user-mailbox-id", required=True, help='Mailbox id or "me"')
    folder_delete.add_argument("--folder-id", required=True, help="Folder id")
    folder_delete.set_defaults(handler=_commands._cmd_folder_delete)

    contact = mail_sub.add_parser("contact", help="Mailbox contact operations")
    contact_sub = contact.add_subparsers(dest="mail_contact_command")
    contact_sub.required = True

    contact_list = contact_sub.add_parser("list", help="List mailbox contacts", parents=[shared])
    contact_list.add_argument("--user-mailbox-id", required=True, help='Mailbox id or "me"')
    _add_paging_args(contact_list, include_all=True)
    contact_list.set_defaults(handler=_commands._cmd_contact_list)

    contact_create = contact_sub.add_parser("create", help="Create mailbox contact", parents=[shared])
    contact_create.add_argument("--user-mailbox-id", required=True, help='Mailbox id or "me"')
    _add_json_source_args(contact_create, name="contact", label="Contact body")
    contact_create.set_defaults(handler=_commands._cmd_contact_create)

    contact_update = contact_sub.add_parser("update", help="Update mailbox contact", parents=[shared])
    contact_update.add_argument("--user-mailbox-id", required=True, help='Mailbox id or "me"')
    contact_update.add_argument("--mail-contact-id", required=True, help="Mailbox contact id")
    _add_json_source_args(contact_update, name="contact", label="Contact patch body")
    contact_update.set_defaults(handler=_commands._cmd_contact_update)

    contact_delete = contact_sub.add_parser("delete", help="Delete mailbox contact", parents=[shared])
    contact_delete.add_argument("--user-mailbox-id", required=True, help='Mailbox id or "me"')
    contact_delete.add_argument("--mail-contact-id", required=True, help="Mailbox contact id")
    contact_delete.set_defaults(handler=_commands._cmd_contact_delete)

    rule = mail_sub.add_parser("rule", help="Incoming mail rule operations")
    rule_sub = rule.add_subparsers(dest="mail_rule_command")
    rule_sub.required = True

    rule_list = rule_sub.add_parser("list", help="List inbox rules", parents=[shared])
    rule_list.add_argument("--user-mailbox-id", required=True, help='Mailbox id or "me"')
    _add_paging_args(rule_list, include_all=True)
    rule_list.set_defaults(handler=_commands._cmd_rule_list)

    rule_create = rule_sub.add_parser("create", help="Create inbox rule", parents=[shared])
    rule_create.add_argument("--user-mailbox-id", required=True, help='Mailbox id or "me"')
    _add_json_source_args(rule_create, name="rule", label="Rule body")
    rule_create.set_defaults(handler=_commands._cmd_rule_create)

    rule_update = rule_sub.add_parser("update", help="Update inbox rule", parents=[shared])
    rule_update.add_argument("--user-mailbox-id", required=True, help='Mailbox id or "me"')
    rule_update.add_argument("--rule-id", required=True, help="Rule id")
    _add_json_source_args(rule_update, name="rule", label="Rule body")
    rule_update.set_defaults(handler=_commands._cmd_rule_update)

    rule_delete = rule_sub.add_parser("delete", help="Delete inbox rule", parents=[shared])
    rule_delete.add_argument("--user-mailbox-id", required=True, help='Mailbox id or "me"')
    rule_delete.add_argument("--rule-id", required=True, help="Rule id")
    rule_delete.set_defaults(handler=_commands._cmd_rule_delete)

    rule_reorder = rule_sub.add_parser("reorder", help="Reorder rules by id sequence", parents=[shared])
    rule_reorder.add_argument("--user-mailbox-id", required=True, help='Mailbox id or "me"')
    _add_id_list_args(rule_reorder, singular_flag="rule-id", dest="rule_ids", label="Rule id")
    rule_reorder.set_defaults(handler=_commands._cmd_rule_reorder)

    event = mail_sub.add_parser("event", help="Mailbox event subscription operations")
    event_sub = event.add_subparsers(dest="mail_event_command")
    event_sub.required = True

    event_get = event_sub.add_parser("get-subscription", help="Get subscription status", parents=[shared])
    event_get.add_argument("--user-mailbox-id", required=True, help='Mailbox id or "me"')
    event_get.set_defaults(handler=_commands._cmd_event_get_subscription)

    event_subscribe = event_sub.add_parser("subscribe", help="Subscribe mailbox event", parents=[shared])
    event_subscribe.add_argument("--user-mailbox-id", required=True, help='Mailbox id or "me"')
    event_subscribe.add_argument("--event-type", type=int, default=1, help="Event type, default 1")
    event_subscribe.set_defaults(handler=_commands._cmd_event_subscribe)

    event_unsubscribe = event_sub.add_parser("unsubscribe", help="Unsubscribe mailbox event", parents=[shared])
    event_unsubscribe.add_argument("--user-mailbox-id", required=True, help='Mailbox id or "me"')
    event_unsubscribe.add_argument("--event-type", type=int, default=1, help="Event type, default 1")
    event_unsubscribe.set_defaults(handler=_commands._cmd_event_unsubscribe)

    group = mail_sub.add_parser("group", help="Mail group operations")
    group_sub = group.add_subparsers(dest="mail_group_command")
    group_sub.required = True

    group_list = group_sub.add_parser("list", help="List mail groups", parents=[shared])
    _add_paging_args(group_list, include_all=True)
    group_list.set_defaults(handler=_commands._cmd_group_list)

    group_get = group_sub.add_parser("get", help="Get one mail group", parents=[shared])
    group_get.add_argument("--mailgroup-id", required=True, help="Mail group id or group email")
    group_get.set_defaults(handler=_commands._cmd_group_get)

    group_create = group_sub.add_parser("create", help="Create mail group", parents=[shared])
    _add_json_source_args(group_create, name="mailgroup", label="Mail group body")
    group_create.set_defaults(handler=_commands._cmd_group_create)

    group_update = group_sub.add_parser("update", help="Patch mail group", parents=[shared])
    group_update.add_argument("--mailgroup-id", required=True, help="Mail group id or group email")
    _add_json_source_args(group_update, name="mailgroup", label="Mail group patch body")
    group_update.set_defaults(handler=_commands._cmd_group_update)

    group_replace = group_sub.add_parser("replace", help="Replace mail group", parents=[shared])
    group_replace.add_argument("--mailgroup-id", required=True, help="Mail group id or group email")
    _add_json_source_args(group_replace, name="mailgroup", label="Mail group body")
    group_replace.set_defaults(handler=_commands._cmd_group_replace)

    group_delete = group_sub.add_parser("delete", help="Delete mail group", parents=[shared])
    group_delete.add_argument("--mailgroup-id", required=True, help="Mail group id or group email")
    group_delete.set_defaults(handler=_commands._cmd_group_delete)

    group_alias = group_sub.add_parser("alias", help="Mail group alias operations")
    group_alias_sub = group_alias.add_subparsers(dest="mail_group_alias_command")
    group_alias_sub.required = True

    group_alias_list = group_alias_sub.add_parser("list", help="List mail group aliases", parents=[shared])
    group_alias_list.add_argument("--mailgroup-id", required=True, help="Mail group id or group email")
    group_alias_list.set_defaults(handler=_commands._cmd_group_alias_list)

    group_alias_create = group_alias_sub.add_parser("create", help="Create mail group alias", parents=[shared])
    group_alias_create.add_argument("--mailgroup-id", required=True, help="Mail group id or group email")
    group_alias_create.add_argument("--email-alias", help="Alias email address, maps to request field email_alias")
    _add_json_source_args(
        group_alias_create,
        name="alias",
        label="Alias body",
        json_help='Alias JSON object, e.g. {"email_alias":"alias@example.com"}',
    )
    group_alias_create.set_defaults(handler=_commands._cmd_group_alias_create)

    group_alias_delete = group_alias_sub.add_parser("delete", help="Delete mail group alias", parents=[shared])
    group_alias_delete.add_argument("--mailgroup-id", required=True, help="Mail group id or group email")
    group_alias_delete.add_argument("--alias-id", required=True, help="Alias id")
    group_alias_delete.set_defaults(handler=_commands._cmd_group_alias_delete)

    group_member = group_sub.add_parser("member", help="Mail group member operations")
    group_member_sub = group_member.add_subparsers(dest="mail_group_member_command")
    group_member_sub.required = True

    group_member_list = group_member_sub.add_parser("list", help="List mail group members", parents=[shared])
    group_member_list.add_argument("--mailgroup-id", required=True, help="Mail group id or group email")
    _add_user_identity_args(group_member_list, include_department=True)
    _add_paging_args(group_member_list, include_all=True)
    group_member_list.set_defaults(handler=_commands._cmd_group_member_list)

    group_member_get = group_member_sub.add_parser("get", help="Get one mail group member", parents=[shared])
    group_member_get.add_argument("--mailgroup-id", required=True, help="Mail group id or group email")
    group_member_get.add_argument("--member-id", required=True, help="Member id")
    _add_user_identity_args(group_member_get, include_department=True)
    group_member_get.set_defaults(handler=_commands._cmd_group_member_get)

    group_member_create = group_member_sub.add_parser("create", help="Create mail group member", parents=[shared])
    group_member_create.add_argument("--mailgroup-id", required=True, help="Mail group id or group email")
    _add_user_identity_args(group_member_create, include_department=True)
    _add_json_source_args(group_member_create, name="member", label="Member body")
    group_member_create.set_defaults(handler=_commands._cmd_group_member_create)

    group_member_batch_create = group_member_sub.add_parser("batch-create", help="Batch create mail group members", parents=[shared])
    group_member_batch_create.add_argument("--mailgroup-id", required=True, help="Mail group id or group email")
    _add_user_identity_args(group_member_batch_create, include_department=True)
    _add_json_array_source_args(group_member_batch_create, name="items", label="Member items")
    group_member_batch_create.set_defaults(handler=_commands._cmd_group_member_batch_create)

    group_member_delete = group_member_sub.add_parser("delete", help="Delete one mail group member", parents=[shared])
    group_member_delete.add_argument("--mailgroup-id", required=True, help="Mail group id or group email")
    group_member_delete.add_argument("--member-id", required=True, help="Member id")
    _add_user_identity_args(group_member_delete, include_department=True)
    group_member_delete.set_defaults(handler=_commands._cmd_group_member_delete)

    group_member_batch_delete = group_member_sub.add_parser("batch-delete", help="Batch delete mail group members", parents=[shared])
    group_member_batch_delete.add_argument("--mailgroup-id", required=True, help="Mail group id or group email")
    _add_user_identity_args(group_member_batch_delete, include_department=True)
    _add_id_list_args(group_member_batch_delete, singular_flag="member-id", dest="member_ids", label="Member id")
    group_member_batch_delete.set_defaults(handler=_commands._cmd_group_member_batch_delete)

    group_permission = group_sub.add_parser("permission-member", help="Mail group permission-member operations")
    group_permission_sub = group_permission.add_subparsers(dest="mail_group_permission_member_command")
    group_permission_sub.required = True

    group_permission_list = group_permission_sub.add_parser("list", help="List permission members", parents=[shared])
    group_permission_list.add_argument("--mailgroup-id", required=True, help="Mail group id or group email")
    _add_user_identity_args(group_permission_list, include_department=True)
    _add_paging_args(group_permission_list, include_all=True)
    group_permission_list.set_defaults(handler=_commands._cmd_group_permission_member_list)

    group_permission_get = group_permission_sub.add_parser("get", help="Get one permission member", parents=[shared])
    group_permission_get.add_argument("--mailgroup-id", required=True, help="Mail group id or group email")
    group_permission_get.add_argument("--member-id", required=True, help="Permission member id")
    _add_user_identity_args(group_permission_get, include_department=True)
    group_permission_get.set_defaults(handler=_commands._cmd_group_permission_member_get)

    group_permission_create = group_permission_sub.add_parser("create", help="Create permission member", parents=[shared])
    group_permission_create.add_argument("--mailgroup-id", required=True, help="Mail group id or group email")
    _add_user_identity_args(group_permission_create, include_department=True)
    _add_json_source_args(group_permission_create, name="member", label="Permission member body")
    group_permission_create.set_defaults(handler=_commands._cmd_group_permission_member_create)

    group_permission_batch_create = group_permission_sub.add_parser("batch-create", help="Batch create permission members", parents=[shared])
    group_permission_batch_create.add_argument("--mailgroup-id", required=True, help="Mail group id or group email")
    _add_user_identity_args(group_permission_batch_create, include_department=True)
    _add_json_array_source_args(group_permission_batch_create, name="items", label="Permission member items")
    group_permission_batch_create.set_defaults(handler=_commands._cmd_group_permission_member_batch_create)

    group_permission_delete = group_permission_sub.add_parser("delete", help="Delete one permission member", parents=[shared])
    group_permission_delete.add_argument("--mailgroup-id", required=True, help="Mail group id or group email")
    group_permission_delete.add_argument("--member-id", required=True, help="Permission member id")
    _add_user_identity_args(group_permission_delete, include_department=True)
    group_permission_delete.set_defaults(handler=_commands._cmd_group_permission_member_delete)

    group_permission_batch_delete = group_permission_sub.add_parser("batch-delete", help="Batch delete permission members", parents=[shared])
    group_permission_batch_delete.add_argument("--mailgroup-id", required=True, help="Mail group id or group email")
    _add_user_identity_args(group_permission_batch_delete, include_department=True)
    _add_id_list_args(group_permission_batch_delete, singular_flag="member-id", dest="member_ids", label="Permission member id")
    group_permission_batch_delete.set_defaults(handler=_commands._cmd_group_permission_member_batch_delete)

    group_manager = group_sub.add_parser("manager", help="Mail group manager operations")
    group_manager_sub = group_manager.add_subparsers(dest="mail_group_manager_command")
    group_manager_sub.required = True

    group_manager_list = group_manager_sub.add_parser("list", help="List mail group managers", parents=[shared])
    group_manager_list.add_argument("--mailgroup-id", required=True, help="Mail group id or group email")
    group_manager_list.add_argument("--user-id-type", choices=_USER_ID_TYPE_CHOICES, help="Optional user_id_type")
    _add_paging_args(group_manager_list, include_all=True)
    group_manager_list.set_defaults(handler=_commands._cmd_group_manager_list)

    group_manager_batch_create = group_manager_sub.add_parser("batch-create", help="Batch create mail group managers", parents=[shared])
    group_manager_batch_create.add_argument("--mailgroup-id", required=True, help="Mail group id or group email")
    group_manager_batch_create.add_argument("--user-id-type", choices=_USER_ID_TYPE_CHOICES, help="Optional user_id_type")
    _add_json_array_source_args(group_manager_batch_create, name="managers", label="Manager items")
    group_manager_batch_create.set_defaults(handler=_commands._cmd_group_manager_batch_create)

    group_manager_batch_delete = group_manager_sub.add_parser("batch-delete", help="Batch delete mail group managers", parents=[shared])
    group_manager_batch_delete.add_argument("--mailgroup-id", required=True, help="Mail group id or group email")
    group_manager_batch_delete.add_argument("--user-id-type", choices=_USER_ID_TYPE_CHOICES, help="Optional user_id_type")
    _add_json_array_source_args(group_manager_batch_delete, name="managers", label="Manager items")
    group_manager_batch_delete.set_defaults(handler=_commands._cmd_group_manager_batch_delete)

    public_mailbox = mail_sub.add_parser("public-mailbox", help="Public mailbox operations")
    public_mailbox_sub = public_mailbox.add_subparsers(dest="mail_public_mailbox_command")
    public_mailbox_sub.required = True

    public_mailbox_list = public_mailbox_sub.add_parser("list", help="List public mailboxes", parents=[shared])
    _add_paging_args(public_mailbox_list, include_all=True)
    public_mailbox_list.set_defaults(handler=_commands._cmd_public_mailbox_list)

    public_mailbox_get = public_mailbox_sub.add_parser("get", help="Get one public mailbox", parents=[shared])
    public_mailbox_get.add_argument("--public-mailbox-id", required=True, help="Public mailbox id or email")
    public_mailbox_get.set_defaults(handler=_commands._cmd_public_mailbox_get)

    public_mailbox_create = public_mailbox_sub.add_parser("create", help="Create public mailbox", parents=[shared])
    _add_json_source_args(public_mailbox_create, name="public_mailbox", label="Public mailbox body")
    public_mailbox_create.set_defaults(handler=_commands._cmd_public_mailbox_create)

    public_mailbox_update = public_mailbox_sub.add_parser("update", help="Patch public mailbox", parents=[shared])
    public_mailbox_update.add_argument("--public-mailbox-id", required=True, help="Public mailbox id or email")
    _add_json_source_args(public_mailbox_update, name="public_mailbox", label="Public mailbox patch body")
    public_mailbox_update.set_defaults(handler=_commands._cmd_public_mailbox_update)

    public_mailbox_replace = public_mailbox_sub.add_parser("replace", help="Replace public mailbox", parents=[shared])
    public_mailbox_replace.add_argument("--public-mailbox-id", required=True, help="Public mailbox id or email")
    _add_json_source_args(public_mailbox_replace, name="public_mailbox", label="Public mailbox body")
    public_mailbox_replace.set_defaults(handler=_commands._cmd_public_mailbox_replace)

    public_mailbox_remove = public_mailbox_sub.add_parser("remove-to-recycle-bin", help="Move public mailbox to recycle bin", parents=[shared])
    public_mailbox_remove.add_argument("--public-mailbox-id", required=True, help="Public mailbox id or email")
    public_mailbox_remove.add_argument("--to-mail-address", help="Optional mailbox that receives transferred mail before recycle-bin removal")
    _add_json_source_args(
        public_mailbox_remove,
        name="options",
        label="Remove-to-recycle-bin body",
        json_help='Options JSON object, e.g. {"to_mail_address":"archive@example.com"}',
    )
    public_mailbox_remove.set_defaults(handler=_commands._cmd_public_mailbox_remove_to_recycle_bin)

    public_mailbox_delete = public_mailbox_sub.add_parser("delete", help="Permanently delete public mailbox", parents=[shared])
    public_mailbox_delete.add_argument("--public-mailbox-id", required=True, help="Public mailbox id or email")
    public_mailbox_delete.set_defaults(handler=_commands._cmd_public_mailbox_delete)

    public_alias = public_mailbox_sub.add_parser("alias", help="Public mailbox alias operations")
    public_alias_sub = public_alias.add_subparsers(dest="mail_public_mailbox_alias_command")
    public_alias_sub.required = True

    public_alias_list = public_alias_sub.add_parser("list", help="List public mailbox aliases", parents=[shared])
    public_alias_list.add_argument("--public-mailbox-id", required=True, help="Public mailbox id or email")
    public_alias_list.set_defaults(handler=_commands._cmd_public_mailbox_alias_list)

    public_alias_create = public_alias_sub.add_parser("create", help="Create public mailbox alias", parents=[shared])
    public_alias_create.add_argument("--public-mailbox-id", required=True, help="Public mailbox id or email")
    public_alias_create.add_argument("--email-alias", help="Alias email address, maps to request field email_alias")
    _add_json_source_args(
        public_alias_create,
        name="alias",
        label="Alias body",
        json_help='Alias JSON object, e.g. {"email_alias":"help@example.com"}',
    )
    public_alias_create.set_defaults(handler=_commands._cmd_public_mailbox_alias_create)

    public_alias_delete = public_alias_sub.add_parser("delete", help="Delete public mailbox alias", parents=[shared])
    public_alias_delete.add_argument("--public-mailbox-id", required=True, help="Public mailbox id or email")
    public_alias_delete.add_argument("--alias-id", required=True, help="Alias id")
    public_alias_delete.set_defaults(handler=_commands._cmd_public_mailbox_alias_delete)

    public_member = public_mailbox_sub.add_parser("member", help="Public mailbox member operations")
    public_member_sub = public_member.add_subparsers(dest="mail_public_mailbox_member_command")
    public_member_sub.required = True

    public_member_list = public_member_sub.add_parser("list", help="List public mailbox members", parents=[shared])
    public_member_list.add_argument("--public-mailbox-id", required=True, help="Public mailbox id or email")
    public_member_list.add_argument("--user-id-type", choices=_USER_ID_TYPE_CHOICES, help="Optional user_id_type")
    _add_paging_args(public_member_list, include_all=True)
    public_member_list.set_defaults(handler=_commands._cmd_public_mailbox_member_list)

    public_member_get = public_member_sub.add_parser("get", help="Get one public mailbox member", parents=[shared])
    public_member_get.add_argument("--public-mailbox-id", required=True, help="Public mailbox id or email")
    public_member_get.add_argument("--member-id", required=True, help="Member id")
    public_member_get.add_argument("--user-id-type", choices=_USER_ID_TYPE_CHOICES, help="Optional user_id_type")
    public_member_get.set_defaults(handler=_commands._cmd_public_mailbox_member_get)

    public_member_create = public_member_sub.add_parser("create", help="Create public mailbox member", parents=[shared])
    public_member_create.add_argument("--public-mailbox-id", required=True, help="Public mailbox id or email")
    public_member_create.add_argument("--user-id-type", choices=_USER_ID_TYPE_CHOICES, help="Optional user_id_type")
    _add_json_source_args(public_member_create, name="member", label="Member body")
    public_member_create.set_defaults(handler=_commands._cmd_public_mailbox_member_create)

    public_member_batch_create = public_member_sub.add_parser("batch-create", help="Batch create public mailbox members", parents=[shared])
    public_member_batch_create.add_argument("--public-mailbox-id", required=True, help="Public mailbox id or email")
    public_member_batch_create.add_argument("--user-id-type", choices=_USER_ID_TYPE_CHOICES, help="Optional user_id_type")
    _add_json_array_source_args(public_member_batch_create, name="items", label="Member items")
    public_member_batch_create.set_defaults(handler=_commands._cmd_public_mailbox_member_batch_create)

    public_member_delete = public_member_sub.add_parser("delete", help="Delete one public mailbox member", parents=[shared])
    public_member_delete.add_argument("--public-mailbox-id", required=True, help="Public mailbox id or email")
    public_member_delete.add_argument("--member-id", required=True, help="Member id")
    public_member_delete.add_argument("--user-id-type", choices=_USER_ID_TYPE_CHOICES, help="Optional user_id_type")
    public_member_delete.set_defaults(handler=_commands._cmd_public_mailbox_member_delete)

    public_member_batch_delete = public_member_sub.add_parser("batch-delete", help="Batch delete public mailbox members", parents=[shared])
    public_member_batch_delete.add_argument("--public-mailbox-id", required=True, help="Public mailbox id or email")
    public_member_batch_delete.add_argument("--user-id-type", choices=_USER_ID_TYPE_CHOICES, help="Optional user_id_type")
    _add_id_list_args(public_member_batch_delete, singular_flag="member-id", dest="member_ids", label="Member id")
    public_member_batch_delete.set_defaults(handler=_commands._cmd_public_mailbox_member_batch_delete)

    public_member_clear = public_member_sub.add_parser("clear", help="Delete all public mailbox members", parents=[shared])
    public_member_clear.add_argument("--public-mailbox-id", required=True, help="Public mailbox id or email")
    public_member_clear.set_defaults(handler=_commands._cmd_public_mailbox_member_clear)


__all__ = ["_build_mail_commands"]
