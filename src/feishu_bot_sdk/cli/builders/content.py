from __future__ import annotations

import argparse

from ..commands import (
    _cmd_bitable_copy_app,
    _cmd_bitable_create_from_csv,
    _cmd_bitable_create_record,
    _cmd_bitable_create_table,
    _cmd_bitable_create_view,
    _cmd_bitable_delete_view,
    _cmd_bitable_get_app,
    _cmd_bitable_get_field,
    _cmd_bitable_get_view,
    _cmd_bitable_grant_edit,
    _cmd_bitable_list_records,
    _cmd_bitable_list_views,
    _cmd_bitable_update_app,
    _cmd_bitable_update_view,
    _cmd_docx_batch_update,
    _cmd_docx_convert_content,
    _cmd_docx_create,
    _cmd_docx_create_children,
    _cmd_docx_create_descendant,
    _cmd_docx_delete_children_range,
    _cmd_docx_get,
    _cmd_docx_get_block,
    _cmd_docx_get_content,
    _cmd_docx_grant_edit,
    _cmd_docx_insert_content,
    _cmd_docx_list_blocks,
    _cmd_docx_list_children,
    _cmd_docx_raw_content,
    _cmd_docx_replace_file,
    _cmd_docx_replace_image,
    _cmd_docx_set_block_text,
    _cmd_docx_set_title,
    _cmd_docx_update_block,
    _cmd_drive_copy,
    _cmd_drive_create_export_task,
    _cmd_drive_create_folder,
    _cmd_drive_create_import_task,
    _cmd_drive_delete,
    _cmd_drive_download_export_file,
    _cmd_drive_download_file,
    _cmd_drive_get_export_task,
    _cmd_drive_get_import_task,
    _cmd_drive_grant_edit,
    _cmd_drive_list_files,
    _cmd_drive_list_members,
    _cmd_drive_meta,
    _cmd_drive_move,
    _cmd_drive_shortcut,
    _cmd_drive_stats,
    _cmd_drive_upload_file,
    _cmd_drive_version_create,
    _cmd_drive_version_delete,
    _cmd_drive_version_get,
    _cmd_drive_version_list,
    _cmd_drive_view_records,
    _cmd_wiki_get_node,
    _cmd_wiki_list_nodes,
    _cmd_wiki_list_spaces,
    _cmd_wiki_search_nodes,
)
from ..settings import HELP_FORMATTER as _HELP_FORMATTER

_ID_TYPE_CHOICES = ("open_id", "user_id", "union_id")
_DOC_TYPE_CHOICES = ("docx", "sheet", "bitable", "file", "wiki_doc", "wiki_sheet")
_CONTENT_TYPE_CHOICES = ("markdown", "html")
_BOOL_CHOICES = ("true", "false")
_DRIVE_RESOURCE_CHOICES = ("bitable", "docx")
_PERMISSION_CHOICES = ("view", "edit", "full_access")
_DRIVE_FILE_TYPE_CHOICES = ("doc", "docx", "sheet", "bitable", "mindnote", "folder", "file", "slides")
_DRIVE_OBJ_TYPE_CHOICES = ("docx", "sheet", "bitable")
_VIEW_TYPE_CHOICES = ("grid", "kanban", "gallery", "gantt", "form")


def _add_docx_write_args(parser: argparse.ArgumentParser, *, include_user_id_type: bool = True) -> None:
    parser.add_argument("--document-revision-id", type=int, help="Optional document revision id")
    parser.add_argument("--client-token", help="Optional idempotency token")
    if include_user_id_type:
        parser.add_argument("--user-id-type", choices=_ID_TYPE_CHOICES, help="Optional user_id_type")


def _add_text_source_args(
    parser: argparse.ArgumentParser,
    *,
    name: str,
    label: str,
) -> None:
    flag_name = name.replace("_", "-")
    parser.add_argument(f"--{flag_name}", help=f"{label} text")
    parser.add_argument(f"--{flag_name}-file", help=f"{label} file path")
    parser.add_argument(f"--{flag_name}-stdin", action="store_true", help=f"Read {label} from stdin")


def _add_json_source_args(
    parser: argparse.ArgumentParser,
    *,
    name: str,
    label: str,
    json_help: str | None = None,
) -> None:
    flag_name = name.replace("_", "-")
    parser.add_argument(f"--{flag_name}-json", help=json_help or f"{label} JSON")
    parser.add_argument(f"--{flag_name}-file", help=f"{label} JSON file path")
    parser.add_argument(f"--{flag_name}-stdin", action="store_true", help=f"Read {label} JSON from stdin")


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
        description="Create a bitable app with one table from a CSV file. Returns: app_token, app_url",
        formatter_class=_HELP_FORMATTER,
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
    create_table.add_argument("--table-json", help='Table JSON, e.g. {"name":"Tasks","fields":[{"field_name":"Title","type":1}]}')
    create_table.add_argument("--table-file", help="Table JSON file path")
    create_table.add_argument("--table-stdin", action="store_true", help="Read table JSON from stdin")
    create_table.set_defaults(handler=_cmd_bitable_create_table)

    create_record = bitable_sub.add_parser("create-record", help="Create record", parents=[shared])
    create_record.add_argument("--app-token", required=True, help="Bitable app_token")
    create_record.add_argument("--table-id", required=True, help="Bitable table_id")
    create_record.add_argument("--fields-json", help='Fields JSON, e.g. {"Title":"Buy milk","Status":"Todo"}')
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
    list_records.add_argument("--filter", help='Filter expression, e.g. AND(CurrentValue.[Status]="Todo",CurrentValue.[Priority]>1)')
    list_records.add_argument("--sort", help='Sort JSON array, e.g. [{"field_name":"Created","desc":true}]')
    list_records.add_argument("--field-names", help='Field names JSON array, e.g. ["Title","Status","Assignee"]')
    list_records.add_argument(
        "--text-field-as-array",
        choices=_BOOL_CHOICES,
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

    get_app = bitable_sub.add_parser("get-app", help="Get bitable app info", parents=[shared])
    get_app.add_argument("--app-token", required=True, help="Bitable app_token")
    get_app.set_defaults(handler=_cmd_bitable_get_app)

    update_app = bitable_sub.add_parser("update-app", help="Update bitable app", parents=[shared])
    update_app.add_argument("--app-token", required=True, help="Bitable app_token")
    update_app.add_argument("--name", help="New app name")
    update_app.set_defaults(handler=_cmd_bitable_update_app)

    copy_app = bitable_sub.add_parser("copy-app", help="Copy bitable app", parents=[shared])
    copy_app.add_argument("--app-token", required=True, help="Bitable app_token")
    copy_app.add_argument("--name", help="Optional copy name")
    copy_app.add_argument("--folder-token", help="Optional target folder token")
    copy_app.set_defaults(handler=_cmd_bitable_copy_app)

    list_views = bitable_sub.add_parser("list-views", help="List views in a table", parents=[shared])
    list_views.add_argument("--app-token", required=True, help="Bitable app_token")
    list_views.add_argument("--table-id", required=True, help="Table ID")
    list_views.add_argument("--page-size", type=int, help="Page size")
    list_views.add_argument("--page-token", help="Page token")
    list_views.add_argument("--all", action="store_true", help="Auto paginate and return all items")
    list_views.set_defaults(handler=_cmd_bitable_list_views)

    get_view = bitable_sub.add_parser("get-view", help="Get a view", parents=[shared])
    get_view.add_argument("--app-token", required=True, help="Bitable app_token")
    get_view.add_argument("--table-id", required=True, help="Table ID")
    get_view.add_argument("--view-id", required=True, help="View ID")
    get_view.set_defaults(handler=_cmd_bitable_get_view)

    create_view = bitable_sub.add_parser("create-view", help="Create a view", parents=[shared])
    create_view.add_argument("--app-token", required=True, help="Bitable app_token")
    create_view.add_argument("--table-id", required=True, help="Table ID")
    create_view.add_argument("--view-name", required=True, help="View name")
    create_view.add_argument("--view-type", choices=_VIEW_TYPE_CHOICES, help="View type")
    create_view.set_defaults(handler=_cmd_bitable_create_view)

    update_view = bitable_sub.add_parser("update-view", help="Update a view", parents=[shared])
    update_view.add_argument("--app-token", required=True, help="Bitable app_token")
    update_view.add_argument("--table-id", required=True, help="Table ID")
    update_view.add_argument("--view-id", required=True, help="View ID")
    update_view.add_argument("--view-name", required=True, help="New view name")
    update_view.set_defaults(handler=_cmd_bitable_update_view)

    delete_view = bitable_sub.add_parser("delete-view", help="Delete a view", parents=[shared])
    delete_view.add_argument("--app-token", required=True, help="Bitable app_token")
    delete_view.add_argument("--table-id", required=True, help="Table ID")
    delete_view.add_argument("--view-id", required=True, help="View ID")
    delete_view.set_defaults(handler=_cmd_bitable_delete_view)

    get_field = bitable_sub.add_parser("get-field", help="Get a field", parents=[shared])
    get_field.add_argument("--app-token", required=True, help="Bitable app_token")
    get_field.add_argument("--table-id", required=True, help="Table ID")
    get_field.add_argument("--field-id", required=True, help="Field ID")
    get_field.set_defaults(handler=_cmd_bitable_get_field)


def _build_docx_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    shared: argparse.ArgumentParser,
) -> None:
    docx_parser = subparsers.add_parser(
        "docx",
        help="Docx document and block operations",
        description=(
            "Docx document, block, content-convert, and asset replacement operations.\n"
            "Write flows use the official convert -> create_descendant -> replace_image workflow."
        ),
        formatter_class=_HELP_FORMATTER,
        epilog=(
            "Examples:\n"
            "  feishu docx create --title \"Daily\" --folder-token fld_xxx --format json\n"
            "  feishu docx insert-content --document-id doccn_xxx --content-file ./report.md --content-type markdown --format json\n"
            "  feishu docx list-blocks --document-id doccn_xxx --all --format json"
        ),
    )
    docx_sub = docx_parser.add_subparsers(dest="docx_command")
    docx_sub.required = True

    create = docx_sub.add_parser(
        "create",
        help="Create docx document",
        parents=[shared],
        description="Create a new docx document. Returns: document with 'document_id'",
        formatter_class=_HELP_FORMATTER,
    )
    create.add_argument("--title", required=True, help="Document title")
    create.add_argument("--folder-token", help="Optional target folder token")
    create.set_defaults(handler=_cmd_docx_create)

    get_doc = docx_sub.add_parser("get", help="Get document metadata", parents=[shared])
    get_doc.add_argument("--document-id", required=True, help="Document token")
    get_doc.set_defaults(handler=_cmd_docx_get)

    raw_content = docx_sub.add_parser("raw-content", help="Get document plain text content", parents=[shared])
    raw_content.add_argument("--document-id", required=True, help="Document token")
    raw_content.add_argument("--lang", help="Optional language")
    raw_content.add_argument("--output", help="Write content to file")
    raw_content.set_defaults(handler=_cmd_docx_raw_content)

    get_content = docx_sub.add_parser("get-content", help="Export docs content", parents=[shared])
    get_content.add_argument("--doc-token", required=True, help="Doc token")
    get_content.add_argument(
        "--doc-type",
        default="docx",
        choices=_DOC_TYPE_CHOICES,
        help="docx/sheet/bitable/file/wiki_doc/wiki_sheet",
    )
    get_content.add_argument(
        "--content-type",
        default="markdown",
        choices=_CONTENT_TYPE_CHOICES,
        help="markdown/html (default: markdown)",
    )
    get_content.add_argument("--lang", help="Optional language")
    get_content.add_argument("--output", help="Write content to file")
    get_content.set_defaults(handler=_cmd_docx_get_content)

    list_blocks = docx_sub.add_parser("list-blocks", help="List document blocks", parents=[shared])
    list_blocks.add_argument("--document-id", required=True, help="Document token")
    list_blocks.add_argument("--page-size", type=int, help="Page size")
    list_blocks.add_argument("--page-token", help="Page token")
    list_blocks.add_argument("--document-revision-id", type=int, help="Optional document revision id")
    list_blocks.add_argument("--user-id-type", choices=_ID_TYPE_CHOICES, help="Optional user_id_type")
    list_blocks.add_argument("--all", action="store_true", help="Auto paginate and return all items")
    list_blocks.set_defaults(handler=_cmd_docx_list_blocks)

    get_block = docx_sub.add_parser("get-block", help="Get a block", parents=[shared])
    get_block.add_argument("--document-id", required=True, help="Document token")
    get_block.add_argument("--block-id", required=True, help="Block id")
    get_block.add_argument("--document-revision-id", type=int, help="Optional document revision id")
    get_block.add_argument("--user-id-type", choices=_ID_TYPE_CHOICES, help="Optional user_id_type")
    get_block.set_defaults(handler=_cmd_docx_get_block)

    list_children = docx_sub.add_parser("list-children", help="List block children", parents=[shared])
    list_children.add_argument("--document-id", required=True, help="Document token")
    list_children.add_argument("--block-id", required=True, help="Parent block id")
    list_children.add_argument("--page-size", type=int, help="Page size")
    list_children.add_argument("--page-token", help="Page token")
    list_children.add_argument("--document-revision-id", type=int, help="Optional document revision id")
    list_children.add_argument("--with-descendants", choices=_BOOL_CHOICES, help="Include all descendant blocks (true/false). Omit = false")
    list_children.add_argument("--user-id-type", choices=_ID_TYPE_CHOICES, help="Optional user_id_type")
    list_children.add_argument("--all", action="store_true", help="Auto paginate and return all items")
    list_children.set_defaults(handler=_cmd_docx_list_children)

    create_children = docx_sub.add_parser("create-children", help="Create direct child blocks", parents=[shared])
    create_children.add_argument("--document-id", required=True, help="Document token")
    create_children.add_argument("--block-id", required=True, help="Parent block id")
    _add_json_source_args(create_children, name="children", label="children", json_help='Children blocks JSON array, e.g. [{"block_type":2,"text":{"elements":[{"text_run":{"content":"Hello"}}]}}]')
    create_children.add_argument("--index", type=int, default=-1, help="Insert index (default: -1)")
    _add_docx_write_args(create_children)
    create_children.set_defaults(handler=_cmd_docx_create_children)

    create_descendant = docx_sub.add_parser("create-descendant", help="Create nested descendant blocks", parents=[shared])
    create_descendant.add_argument("--document-id", required=True, help="Document token")
    create_descendant.add_argument("--block-id", required=True, help="Parent block id")
    _add_json_source_args(create_descendant, name="children_id", label="children_id", json_help='Ordered block IDs, e.g. ["blk_xxx1","blk_xxx2"]')
    _add_json_source_args(create_descendant, name="descendants", label="descendants", json_help='Descendant block map, e.g. {"blk_xxx1":{"block_type":2,"text":{"elements":[{"text_run":{"content":"Hi"}}]}}}')
    create_descendant.add_argument("--index", type=int, default=-1, help="Insert index (default: -1)")
    _add_docx_write_args(create_descendant)
    create_descendant.set_defaults(handler=_cmd_docx_create_descendant)

    update_block = docx_sub.add_parser("update-block", help="Update block content", parents=[shared])
    update_block.add_argument("--document-id", required=True, help="Document token")
    update_block.add_argument("--block-id", required=True, help="Block id")
    _add_json_source_args(update_block, name="operations", label="operations", json_help='Operations JSON array, e.g. [{"replaceText":{"text":"new text"}}]')
    _add_docx_write_args(update_block)
    update_block.set_defaults(handler=_cmd_docx_update_block)

    batch_update = docx_sub.add_parser("batch-update", help="Batch update blocks", parents=[shared])
    batch_update.add_argument("--document-id", required=True, help="Document token")
    _add_json_source_args(batch_update, name="requests", label="requests", json_help='Batch requests JSON array, e.g. [{"requestType":"UpdateTextElementsRequest","updateTextElementsRequest":{...}}]')
    _add_docx_write_args(batch_update)
    batch_update.set_defaults(handler=_cmd_docx_batch_update)

    delete_children = docx_sub.add_parser("delete-children-range", help="Delete a child block range", parents=[shared])
    delete_children.add_argument("--document-id", required=True, help="Document token")
    delete_children.add_argument("--block-id", required=True, help="Parent block id")
    delete_children.add_argument("--start-index", required=True, type=int, help="Start child index")
    delete_children.add_argument("--end-index", required=True, type=int, help="End child index")
    delete_children.add_argument("--document-revision-id", type=int, help="Optional document revision id")
    delete_children.add_argument("--client-token", help="Optional idempotency token")
    delete_children.set_defaults(handler=_cmd_docx_delete_children_range)

    convert_content = docx_sub.add_parser("convert-content", help="Convert markdown/html to blocks", parents=[shared])
    convert_content.add_argument(
        "--content-type",
        default="markdown",
        choices=_CONTENT_TYPE_CHOICES,
        help="markdown/html (default: markdown)",
    )
    _add_text_source_args(convert_content, name="content", label="content")
    convert_content.add_argument("--output", help="Write converted JSON to file")
    convert_content.set_defaults(handler=_cmd_docx_convert_content)

    insert_content = docx_sub.add_parser(
        "insert-content",
        help="Convert markdown/html and insert into docx",
        description=(
            "Convert markdown/html and insert into docx.\n"
            "By default the CLI returns a compact summary to avoid dumping large converted block payloads.\n"
            "Pass --full-response if you need the raw converted/inserted response."
        ),
        parents=[shared],
    )
    insert_content.add_argument("--document-id", required=True, help="Document token")
    insert_content.add_argument("--block-id", help="Parent block id, defaults to document root")
    insert_content.add_argument(
        "--content-type",
        default="markdown",
        choices=_CONTENT_TYPE_CHOICES,
        help="markdown/html (default: markdown)",
    )
    _add_text_source_args(insert_content, name="content", label="content")
    insert_content.add_argument("--index", type=int, default=-1, help="Insert index (default: -1)")
    insert_content.add_argument(
        "--full-response",
        action="store_true",
        help="Return the raw insert response, including converted blocks and inserted batch details",
    )
    _add_docx_write_args(insert_content)
    insert_content.set_defaults(handler=_cmd_docx_insert_content)

    set_title = docx_sub.add_parser("set-title", help="Update document title", parents=[shared])
    set_title.add_argument("--document-id", required=True, help="Document token")
    _add_text_source_args(set_title, name="text", label="title")
    _add_docx_write_args(set_title)
    set_title.set_defaults(handler=_cmd_docx_set_title)

    set_block_text = docx_sub.add_parser("set-block-text", help="Replace block text", parents=[shared])
    set_block_text.add_argument("--document-id", required=True, help="Document token")
    set_block_text.add_argument("--block-id", required=True, help="Block id")
    _add_text_source_args(set_block_text, name="text", label="text")
    _add_docx_write_args(set_block_text)
    set_block_text.set_defaults(handler=_cmd_docx_set_block_text)

    replace_image = docx_sub.add_parser("replace-image", help="Upload and replace image block asset", parents=[shared])
    replace_image.add_argument("--document-id", required=True, help="Document token")
    replace_image.add_argument("--block-id", required=True, help="Image block id")
    replace_image.add_argument("path", help="Local image file path")
    replace_image.add_argument("--file-name", help="Optional override file name")
    replace_image.add_argument("--checksum", help="Optional checksum")
    replace_image.add_argument("--content-type", help="Optional mime type")
    _add_docx_write_args(replace_image)
    replace_image.set_defaults(handler=_cmd_docx_replace_image)

    replace_file = docx_sub.add_parser("replace-file", help="Upload and replace file block asset", parents=[shared])
    replace_file.add_argument("--document-id", required=True, help="Document token")
    replace_file.add_argument("--block-id", required=True, help="File block id")
    replace_file.add_argument("path", help="Local file path")
    replace_file.add_argument("--file-name", help="Optional override file name")
    replace_file.add_argument("--checksum", help="Optional checksum")
    replace_file.add_argument("--content-type", help="Optional mime type")
    _add_docx_write_args(replace_file)
    replace_file.set_defaults(handler=_cmd_docx_replace_file)

    grant_edit = docx_sub.add_parser("grant-edit", help="Grant edit permission on docx", parents=[shared])
    grant_edit.add_argument("--document-id", required=True, help="Document token")
    grant_edit.add_argument("--member-id", required=True, help="Member id")
    grant_edit.add_argument(
        "--member-id-type",
        default="open_id",
        choices=_ID_TYPE_CHOICES,
        help="open_id/user_id/union_id (default: open_id)",
    )
    grant_edit.set_defaults(handler=_cmd_docx_grant_edit)


def _build_drive_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    shared: argparse.ArgumentParser,
) -> None:
    drive_parser = subparsers.add_parser(
        "drive",
        help="Drive file and version operations",
        description=(
            "Drive file upload/download, metadata, task, version, and permission operations.\n"
            "Structured payload commands accept --*-json/--*-file/--*-stdin inputs."
        ),
        formatter_class=_HELP_FORMATTER,
        epilog=(
            "Examples:\n"
            "  feishu drive meta --request-docs-json '[{\"doc_token\":\"doccn_xxx\",\"doc_type\":\"docx\"}]' --with-url true --format json\n"
            "  feishu drive copy doccn_xxx --name \"Report Copy\" --folder-token fld_xxx --format json\n"
            "  feishu drive version-list doccn_xxx --obj-type docx --page-size 50 --all --format json"
        ),
    )
    drive_sub = drive_parser.add_subparsers(dest="drive_command")
    drive_sub.required = True

    upload_file = drive_sub.add_parser("upload-file", help="Upload file to drive", parents=[shared])
    upload_file.add_argument("path", help="File path")
    upload_file.add_argument("--parent-type", required=True, choices=("explorer",), help="Parent type (currently only 'explorer')")
    upload_file.add_argument("--parent-node", required=True, help="Parent node token")
    upload_file.add_argument("--file-name", help="Override file name")
    upload_file.add_argument("--checksum", help="Optional checksum")
    upload_file.add_argument("--content-type", help="Optional mime type")
    upload_file.set_defaults(handler=_cmd_drive_upload_file)

    download_file = drive_sub.add_parser("download-file", help="Download drive file", parents=[shared])
    download_file.add_argument("file_token", help="File token")
    download_file.add_argument("--output", required=True, help="Output file path")
    download_file.set_defaults(handler=_cmd_drive_download_file)

    meta = drive_sub.add_parser("meta", help="Batch query file metadata", parents=[shared])
    _add_json_source_args(meta, name="request_docs", label="request_docs", json_help='Docs to query, e.g. [{"doc_token":"doccn_xxx","doc_type":"docx"}]')
    meta.add_argument("--with-url", choices=_BOOL_CHOICES, help="Include URL in response (true/false). Omit = false")
    meta.add_argument("--user-id-type", choices=_ID_TYPE_CHOICES, help="Optional user_id_type")
    meta.set_defaults(handler=_cmd_drive_meta)

    stats = drive_sub.add_parser("stats", help="Get file statistics", parents=[shared])
    stats.add_argument("file_token", help="File token")
    stats.add_argument("--file-type", required=True, choices=_DRIVE_FILE_TYPE_CHOICES, help="File type")
    stats.set_defaults(handler=_cmd_drive_stats)

    view_records = drive_sub.add_parser("view-records", help="Get file access records", parents=[shared])
    view_records.add_argument("file_token", help="File token")
    view_records.add_argument("--file-type", required=True, choices=_DRIVE_FILE_TYPE_CHOICES, help="File type")
    view_records.add_argument("--page-size", required=True, type=int, help="Page size")
    view_records.add_argument("--page-token", help="Page token")
    view_records.add_argument("--viewer-id-type", choices=_ID_TYPE_CHOICES, help="Optional viewer_id_type")
    view_records.add_argument("--all", action="store_true", help="Auto paginate and return all items")
    view_records.set_defaults(handler=_cmd_drive_view_records)

    copy = drive_sub.add_parser("copy", help="Copy a file", parents=[shared])
    copy.add_argument("file_token", help="Source file token")
    copy.add_argument("--name", required=True, help="Target file name")
    copy.add_argument("--folder-token", required=True, help="Target folder token")
    copy.add_argument("--type", choices=_DRIVE_FILE_TYPE_CHOICES, help="File type")
    _add_json_source_args(copy, name="extra", label="extra")
    copy.add_argument("--user-id-type", choices=_ID_TYPE_CHOICES, help="Optional user_id_type")
    copy.set_defaults(handler=_cmd_drive_copy)

    move = drive_sub.add_parser("move", help="Move a file or folder", parents=[shared])
    move.add_argument("file_token", help="File token")
    move.add_argument("--type", choices=_DRIVE_FILE_TYPE_CHOICES, help="File type")
    move.add_argument("--folder-token", help="Target folder token")
    move.set_defaults(handler=_cmd_drive_move)

    delete = drive_sub.add_parser("delete", help="Delete a file or folder", parents=[shared])
    delete.add_argument("file_token", help="File token")
    delete.add_argument("--type", required=True, choices=_DRIVE_FILE_TYPE_CHOICES, help="File type")
    delete.set_defaults(handler=_cmd_drive_delete)

    shortcut = drive_sub.add_parser("shortcut", help="Create file shortcut", parents=[shared])
    shortcut.add_argument("--parent-token", required=True, help="Shortcut parent folder token")
    shortcut.add_argument("--refer-token", required=True, help="Referenced file token")
    shortcut.add_argument("--refer-type", required=True, choices=_DRIVE_FILE_TYPE_CHOICES, help="Referenced file type")
    shortcut.add_argument("--user-id-type", choices=_ID_TYPE_CHOICES, help="Optional user_id_type")
    shortcut.set_defaults(handler=_cmd_drive_shortcut)

    create_import = drive_sub.add_parser("create-import-task", help="Create drive import task", parents=[shared])
    create_import.add_argument("--task-json", help='Task JSON, e.g. {"file_extension":"xlsx","file_token":"boxcn_xxx","type":"sheet","folder_token":"fld_xxx"}')
    create_import.add_argument("--task-file", help="Task JSON file path")
    create_import.add_argument("--task-stdin", action="store_true", help="Read task JSON from stdin")
    create_import.set_defaults(handler=_cmd_drive_create_import_task)

    get_import = drive_sub.add_parser("get-import-task", help="Get drive import task", parents=[shared])
    get_import.add_argument("ticket", help="Import task ticket")
    get_import.set_defaults(handler=_cmd_drive_get_import_task)

    create_export = drive_sub.add_parser("create-export-task", help="Create drive export task", parents=[shared])
    create_export.add_argument("--task-json", help='Task JSON, e.g. {"file_extension":"pdf","token":"doccn_xxx","type":"docx"}')
    create_export.add_argument("--task-file", help="Task JSON file path")
    create_export.add_argument("--task-stdin", action="store_true", help="Read task JSON from stdin")
    create_export.set_defaults(handler=_cmd_drive_create_export_task)

    get_export = drive_sub.add_parser("get-export-task", help="Get drive export task", parents=[shared])
    get_export.add_argument("ticket", help="Export task ticket")
    get_export.add_argument("--token", help="Optional resource token")
    get_export.set_defaults(handler=_cmd_drive_get_export_task)

    download_export = drive_sub.add_parser("download-export-file", help="Download export task file", parents=[shared])
    download_export.add_argument("file_token", help="Export file token")
    download_export.add_argument("--output", required=True, help="Output file path")
    download_export.set_defaults(handler=_cmd_drive_download_export_file)

    version_create = drive_sub.add_parser("version-create", help="Create document version", parents=[shared])
    version_create.add_argument("file_token", help="File token")
    version_create.add_argument("--name", required=True, help="Version name")
    version_create.add_argument("--obj-type", required=True, choices=_DRIVE_OBJ_TYPE_CHOICES, help="Object type")
    version_create.add_argument("--user-id-type", choices=_ID_TYPE_CHOICES, help="Optional user_id_type")
    version_create.set_defaults(handler=_cmd_drive_version_create)

    version_list = drive_sub.add_parser("version-list", help="List document versions", parents=[shared])
    version_list.add_argument("file_token", help="File token")
    version_list.add_argument("--obj-type", required=True, choices=_DRIVE_OBJ_TYPE_CHOICES, help="Object type")
    version_list.add_argument("--page-size", required=True, type=int, help="Page size")
    version_list.add_argument("--page-token", help="Page token")
    version_list.add_argument("--user-id-type", choices=_ID_TYPE_CHOICES, help="Optional user_id_type")
    version_list.add_argument("--all", action="store_true", help="Auto paginate and return all items")
    version_list.set_defaults(handler=_cmd_drive_version_list)

    version_get = drive_sub.add_parser("version-get", help="Get document version", parents=[shared])
    version_get.add_argument("file_token", help="File token")
    version_get.add_argument("version_id", help="Version id")
    version_get.add_argument("--user-id-type", choices=_ID_TYPE_CHOICES, help="Optional user_id_type")
    version_get.set_defaults(handler=_cmd_drive_version_get)

    version_delete = drive_sub.add_parser("version-delete", help="Delete document version", parents=[shared])
    version_delete.add_argument("file_token", help="File token")
    version_delete.add_argument("version_id", help="Version id")
    version_delete.add_argument("--user-id-type", choices=_ID_TYPE_CHOICES, help="Optional user_id_type")
    version_delete.set_defaults(handler=_cmd_drive_version_delete)

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

    list_files = drive_sub.add_parser("list-files", help="List files in a folder", parents=[shared])
    list_files.add_argument("--folder-token", help="Optional folder token (default: root)")
    list_files.add_argument("--page-size", type=int, help="Page size")
    list_files.add_argument("--page-token", help="Page token")
    list_files.add_argument("--order-by", help="Optional order_by field, e.g. EditedTime")
    list_files.add_argument("--direction", help="Optional direction: ASC or DESC")
    list_files.add_argument("--user-id-type", choices=_ID_TYPE_CHOICES, help="Optional user_id_type")
    list_files.add_argument("--all", action="store_true", help="Auto paginate and return all items")
    list_files.set_defaults(handler=_cmd_drive_list_files)

    create_folder = drive_sub.add_parser(
        "create-folder",
        help="Create a folder",
        parents=[shared],
        description="Create a folder under parent. Returns: {token, url}",
        formatter_class=_HELP_FORMATTER,
    )
    create_folder.add_argument("--name", required=True, help="Folder name")
    create_folder.add_argument("--folder-token", required=True, help="Parent folder token")
    create_folder.set_defaults(handler=_cmd_drive_create_folder)


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
    get_node.add_argument("--obj-type", choices=_DRIVE_OBJ_TYPE_CHOICES, help="Object type")
    get_node.set_defaults(handler=_cmd_wiki_get_node)

    list_nodes = wiki_sub.add_parser("list-nodes", help="List nodes in a space", parents=[shared])
    list_nodes.add_argument("--space-id", required=True, help="Space id")
    list_nodes.add_argument("--parent-node-token", help="Optional parent node token")
    list_nodes.add_argument("--page-size", type=int, help="Page size")
    list_nodes.add_argument("--page-token", help="Page token")
    list_nodes.add_argument("--all", action="store_true", help="Auto paginate and return all items")
    list_nodes.set_defaults(handler=_cmd_wiki_list_nodes)
