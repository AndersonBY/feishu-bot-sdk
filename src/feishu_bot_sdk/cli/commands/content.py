from __future__ import annotations

import argparse
from typing import Any, Mapping

from ...bitable import BitableService
from ...docs_content import DocContentService
from ...docx import DocxService
from ...drive_files import DriveFileService
from ...drive_permissions import DrivePermissionService
from ...wiki import WikiService

from ..runtime import _build_client, _parse_json_object, _resolve_text_input

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


__all__ = [name for name in globals() if name.startswith("_cmd_")]
