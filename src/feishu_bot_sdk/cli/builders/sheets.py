from __future__ import annotations

import argparse

from ..commands.sheets import (
    _cmd_sheets_append,
    _cmd_sheets_create,
    _cmd_sheets_find,
    _cmd_sheets_info,
    _cmd_sheets_list_sheets,
    _cmd_sheets_read,
    _cmd_sheets_write,
)
from ..settings import HELP_FORMATTER as _HELP_FORMATTER


def _build_sheets_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    shared: argparse.ArgumentParser,
) -> None:
    sheets_parser = subparsers.add_parser(
        "sheets",
        help="Spreadsheet operations (Feishu Sheets v2)",
        description=(
            "Spreadsheet operations for reading/writing cell values, listing sheets, and searching.\n"
            "Supports JSON from --*-json/--*-file/--*-stdin."
        ),
        formatter_class=_HELP_FORMATTER,
        epilog=(
            "Examples:\n"
            '  feishu sheets info --token shtcnxxx --format json\n'
            '  feishu sheets list-sheets --token shtcnxxx --format json\n'
            '  feishu sheets read --token shtcnxxx --range "Sheet1!A1:C10" --format json\n'
            '  feishu sheets write --token shtcnxxx --values-json \'{"range":"Sheet1!A1:B2","values":[["a","b"]]}\' --format json\n'
            '  feishu sheets find --token shtcnxxx --sheet-id sheetid --find "keyword" --format json'
        ),
    )
    sheets_sub = sheets_parser.add_subparsers(dest="sheets_command")
    sheets_sub.required = True

    info = sheets_sub.add_parser("info", help="Get spreadsheet info", parents=[shared])
    info.add_argument("--token", required=True, help="Spreadsheet token")
    info.set_defaults(handler=_cmd_sheets_info)

    list_sheets = sheets_sub.add_parser("list-sheets", help="List sheets in spreadsheet", parents=[shared])
    list_sheets.add_argument("--token", required=True, help="Spreadsheet token")
    list_sheets.set_defaults(handler=_cmd_sheets_list_sheets)

    read = sheets_sub.add_parser("read", help="Read cell values", parents=[shared])
    read.add_argument("--token", required=True, help="Spreadsheet token")
    read.add_argument("--range", required=True, help="Range string, e.g. Sheet1!A1:C10")
    read.add_argument("--value-render-option", choices=("ToString", "Formula", "FormattedValue", "UnformattedValue"), help="Value render option")
    read.add_argument("--date-time-render-option", choices=("FormattedString",), help="Datetime render option")
    read.set_defaults(handler=_cmd_sheets_read)

    write = sheets_sub.add_parser("write", help="Write cell values", parents=[shared])
    write.add_argument("--token", required=True, help="Spreadsheet token")
    write.add_argument("--values-json", help='ValueRange JSON, e.g. {"range":"Sheet1!A1:B2","values":[["a","b"],["c","d"]]}')
    write.add_argument("--values-file", help="ValueRange JSON file path")
    write.add_argument("--values-stdin", action="store_true", help="Read ValueRange JSON from stdin")
    write.set_defaults(handler=_cmd_sheets_write)

    append = sheets_sub.add_parser("append", help="Append cell values", parents=[shared])
    append.add_argument("--token", required=True, help="Spreadsheet token")
    append.add_argument("--values-json", help='ValueRange JSON, e.g. {"range":"Sheet1!A1:B2","values":[["a","b"]]}')
    append.add_argument("--values-file", help="ValueRange JSON file path")
    append.add_argument("--values-stdin", action="store_true", help="Read ValueRange JSON from stdin")
    append.add_argument("--insert-data-option", choices=("OVERWRITE", "INSERT_ROWS"), help="Insert data option")
    append.set_defaults(handler=_cmd_sheets_append)

    find = sheets_sub.add_parser("find", help="Find cells matching text", parents=[shared])
    find.add_argument("--token", required=True, help="Spreadsheet token")
    find.add_argument("--sheet-id", required=True, help="Sheet ID")
    find.add_argument("--find", required=True, help="Search text")
    find.add_argument("--find-condition-json", help='Find condition JSON, e.g. {"range":"A1:Z100","match_case":true,"match_entire_cell":false,"search_by_regex":false}')
    find.set_defaults(handler=_cmd_sheets_find)

    create = sheets_sub.add_parser(
        "create",
        help="Create a new spreadsheet",
        parents=[shared],
        description="Create a new spreadsheet. Returns: spreadsheet with 'spreadsheet_token'",
        formatter_class=_HELP_FORMATTER,
    )
    create.add_argument("--title", help="Optional spreadsheet title")
    create.add_argument("--folder-token", help="Optional folder token")
    create.set_defaults(handler=_cmd_sheets_create)
