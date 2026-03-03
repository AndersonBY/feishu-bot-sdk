from __future__ import annotations

import argparse

from ..commands import (
    _cmd_bitable_create_from_csv,
    _cmd_bitable_create_record,
    _cmd_bitable_create_table,
    _cmd_bitable_grant_edit,
    _cmd_bitable_list_records,
    _cmd_docx_append_markdown,
    _cmd_docx_create,
    _cmd_docx_create_from_markdown,
    _cmd_docx_get_markdown,
    _cmd_docx_grant_edit,
    _cmd_drive_create_export_task,
    _cmd_drive_create_import_task,
    _cmd_drive_get_export_task,
    _cmd_drive_get_import_task,
    _cmd_drive_grant_edit,
    _cmd_drive_list_members,
    _cmd_drive_upload_file,
    _cmd_wiki_get_node,
    _cmd_wiki_list_nodes,
    _cmd_wiki_list_spaces,
    _cmd_wiki_search_nodes,
)
from ..settings import HELP_FORMATTER as _HELP_FORMATTER

_ID_TYPE_CHOICES = ("open_id", "user_id", "union_id")
_DOC_TYPE_CHOICES = ("docx", "sheet", "bitable", "file", "wiki_doc", "wiki_sheet")
_DRIVE_RESOURCE_CHOICES = ("bitable", "docx")
_PERMISSION_CHOICES = ("view", "edit", "full_access")


def _build_bitable_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    shared: argparse.ArgumentParser,
) -> None:
    bitable_parser = subparsers.add_parser(
        "bitable",
        help="Bitable operations",
        description=(
            "Bitable operations for app/table/record workflows.\n"
            "Supports JSON from --*-json/--*-file/--*-stdin and auto pagination via --all."
        ),
        formatter_class=_HELP_FORMATTER,
        epilog=(
            "Examples:\n"
            "  feishu bitable create-from-csv ./final.csv --app-name \"Task\" --table-name \"Result\" --format json\n"
            "  echo '{\"Task\":\"Follow up\"}' | feishu bitable create-record --app-token app_xxx --table-id tbl_xxx --fields-stdin --format json\n"
            "  feishu bitable list-records --app-token app_xxx --table-id tbl_xxx --all --format json"
        ),
    )
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
        choices=_ID_TYPE_CHOICES,
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
    create_record.add_argument("--user-id-type", choices=_ID_TYPE_CHOICES, help="Optional user_id_type")
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
    list_records.add_argument("--view-id", help="Optional view id")
    list_records.add_argument("--user-id-type", choices=_ID_TYPE_CHOICES, help="Optional user_id_type")
    list_records.add_argument("--filter", help="Optional filter expression string")
    list_records.add_argument("--sort", help="Optional sort JSON string")
    list_records.add_argument("--field-names", help="Optional field_names JSON array string")
    list_records.add_argument(
        "--text-field-as-array",
        choices=("true", "false"),
        help="Whether to return text field values as arrays",
    )
    list_records.add_argument("--all", action="store_true", help="Auto paginate and return all items")
    list_records.set_defaults(handler=_cmd_bitable_list_records)

    grant_edit = bitable_sub.add_parser("grant-edit", help="Grant edit permission on bitable", parents=[shared])
    grant_edit.add_argument("--app-token", required=True, help="Bitable app_token")
    grant_edit.add_argument("--member-id", required=True, help="Member id")
    grant_edit.add_argument(
        "--member-id-type",
        default="open_id",
        choices=_ID_TYPE_CHOICES,
        help="open_id/user_id/union_id (default: open_id)",
    )
    grant_edit.set_defaults(handler=_cmd_bitable_grant_edit)


def _build_docx_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    shared: argparse.ArgumentParser,
) -> None:
    docx_parser = subparsers.add_parser(
        "docx",
        help="Docx and docs content operations",
        description=(
            "Docx create/append/grant and docs content export operations.\n"
            "Use get-markdown to export content from docs/v1/content."
        ),
        formatter_class=_HELP_FORMATTER,
        epilog=(
            "Examples:\n"
            "  feishu docx create-from-markdown --title \"Daily\" --markdown-file ./report.md --format json\n"
            "  feishu docx grant-edit --document-id doccn_xxx --member-id ou_xxx --member-id-type open_id --format json\n"
            "  feishu docx get-markdown --doc-token doccn_xxx --doc-type docx --format json"
        ),
    )
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
        choices=_ID_TYPE_CHOICES,
        help="open_id/user_id/union_id (default: open_id)",
    )
    grant_edit.set_defaults(handler=_cmd_docx_grant_edit)

    get_markdown = docx_sub.add_parser("get-markdown", help="Get markdown from docs content API", parents=[shared])
    get_markdown.add_argument("--doc-token", required=True, help="doc token")
    get_markdown.add_argument(
        "--doc-type",
        default="docx",
        choices=_DOC_TYPE_CHOICES,
        help="docx/sheet/bitable/file/wiki_doc/wiki_sheet",
    )
    get_markdown.add_argument("--lang", help="Optional language")
    get_markdown.set_defaults(handler=_cmd_docx_get_markdown)


def _build_drive_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    shared: argparse.ArgumentParser,
) -> None:
    drive_parser = subparsers.add_parser(
        "drive",
        help="Drive file and permission operations",
        description=(
            "Drive file upload, import/export task, and permission operations.\n"
            "Task payload commands accept --task-json/--task-file/--task-stdin."
        ),
        formatter_class=_HELP_FORMATTER,
        epilog=(
            "Examples:\n"
            "  feishu drive upload-file ./final.csv --parent-type explorer --parent-node fld_xxx --format json\n"
            "  echo '{\"file_extension\":\"csv\"}' | feishu drive create-import-task --task-stdin --format json\n"
            "  feishu drive grant-edit --token tok_xxx --resource-type docx --member-id ou_xxx --permission edit --format json"
        ),
    )
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
    grant_edit.add_argument(
        "--resource-type",
        required=True,
        choices=_DRIVE_RESOURCE_CHOICES,
        help="Resource type, e.g. bitable/docx",
    )
    grant_edit.add_argument("--member-id", required=True, help="Member id")
    grant_edit.add_argument(
        "--member-id-type",
        default="open_id",
        choices=_ID_TYPE_CHOICES,
        help="open_id/user_id/union_id (default: open_id)",
    )
    grant_edit.add_argument(
        "--permission",
        default="edit",
        choices=_PERMISSION_CHOICES,
        help="Permission value (default: edit)",
    )
    grant_edit.set_defaults(handler=_cmd_drive_grant_edit)

    list_members = drive_sub.add_parser("list-members", help="List permission members", parents=[shared])
    list_members.add_argument("--token", required=True, help="Resource token")
    list_members.add_argument(
        "--resource-type",
        required=True,
        choices=_DRIVE_RESOURCE_CHOICES,
        help="Resource type, e.g. bitable/docx",
    )
    list_members.add_argument("--fields", help="Optional fields")
    list_members.add_argument("--perm-type", help="Optional perm_type")
    list_members.set_defaults(handler=_cmd_drive_list_members)


def _build_wiki_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    shared: argparse.ArgumentParser,
) -> None:
    wiki_parser = subparsers.add_parser(
        "wiki",
        help="Wiki operations",
        description=(
            "Wiki operations for listing spaces/nodes and searching nodes.\n"
            "Use --all to auto paginate and merge all items."
        ),
        formatter_class=_HELP_FORMATTER,
        epilog=(
            "Examples:\n"
            "  feishu wiki list-spaces --all --format json\n"
            "  feishu wiki search-nodes --query \"weekly report\" --space-id spc_xxx --all --format json\n"
            "  feishu wiki list-nodes --space-id spc_xxx --all --format json"
        ),
    )
    wiki_sub = wiki_parser.add_subparsers(dest="wiki_command")
    wiki_sub.required = True

    list_spaces = wiki_sub.add_parser("list-spaces", help="List wiki spaces", parents=[shared])
    list_spaces.add_argument("--page-size", type=int, help="Page size")
    list_spaces.add_argument("--page-token", help="Page token")
    list_spaces.add_argument("--all", action="store_true", help="Auto paginate and return all items")
    list_spaces.set_defaults(handler=_cmd_wiki_list_spaces)

    search_nodes = wiki_sub.add_parser("search-nodes", help="Search wiki nodes", parents=[shared])
    search_nodes.add_argument("--query", required=True, help="Search query")
    search_nodes.add_argument("--space-id", help="Optional space id")
    search_nodes.add_argument("--node-id", help="Optional node id")
    search_nodes.add_argument("--page-size", type=int, help="Page size")
    search_nodes.add_argument("--page-token", help="Page token")
    search_nodes.add_argument("--all", action="store_true", help="Auto paginate and return all items")
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
    list_nodes.add_argument("--all", action="store_true", help="Auto paginate and return all items")
    list_nodes.set_defaults(handler=_cmd_wiki_list_nodes)
