from __future__ import annotations

import argparse
import json
from typing import Any, Mapping

from ...sheets import SheetsService
from ..runtime import _build_client, _parse_json_object


def _cmd_sheets_info(args: argparse.Namespace) -> Mapping[str, Any]:
    service = SheetsService(_build_client(args))
    return service.get_spreadsheet_info(str(args.token))


def _cmd_sheets_list_sheets(args: argparse.Namespace) -> Mapping[str, Any]:
    service = SheetsService(_build_client(args))
    return service.list_sheets(str(args.token))


def _cmd_sheets_read(args: argparse.Namespace) -> Mapping[str, Any]:
    service = SheetsService(_build_client(args))
    return service.read_values(
        str(args.token),
        str(args.range),
        value_render_option=getattr(args, "value_render_option", None),
        date_time_render_option=getattr(args, "date_time_render_option", None),
    )


def _cmd_sheets_write(args: argparse.Namespace) -> Mapping[str, Any]:
    value_range = _parse_json_object(
        json_text=getattr(args, "values_json", None),
        file_path=getattr(args, "values_file", None),
        stdin_enabled=bool(getattr(args, "values_stdin", False)),
        name="values",
        required=True,
    )
    service = SheetsService(_build_client(args))
    return service.write_values(str(args.token), value_range=value_range)


def _cmd_sheets_append(args: argparse.Namespace) -> Mapping[str, Any]:
    value_range = _parse_json_object(
        json_text=getattr(args, "values_json", None),
        file_path=getattr(args, "values_file", None),
        stdin_enabled=bool(getattr(args, "values_stdin", False)),
        name="values",
        required=True,
    )
    service = SheetsService(_build_client(args))
    return service.append_values(
        str(args.token),
        value_range=value_range,
        insert_data_option=getattr(args, "insert_data_option", None),
    )


def _cmd_sheets_find(args: argparse.Namespace) -> Mapping[str, Any]:
    find_condition = None
    find_condition_json = getattr(args, "find_condition_json", None)
    if find_condition_json:
        find_condition = json.loads(str(find_condition_json))
    service = SheetsService(_build_client(args))
    return service.find_cells(
        str(args.token),
        str(args.sheet_id),
        find=str(args.find),
        find_condition=find_condition,
    )


def _cmd_sheets_create(args: argparse.Namespace) -> Mapping[str, Any]:
    service = SheetsService(_build_client(args))
    return service.create_spreadsheet(
        title=getattr(args, "title", None),
        folder_token=getattr(args, "folder_token", None),
    )


__all__ = [name for name in globals() if name.startswith("_cmd_")]
