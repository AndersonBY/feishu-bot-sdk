from __future__ import annotations

from typing import Any

import click

from ..context import build_cli_context, with_runtime_options
from ..runtime.registry import (
    find_method,
    get_service,
    list_schema_paths,
    list_services,
    load_metadata_snapshot,
    summarize_shape,
)
from ..shortcuts import get_shortcut, list_shortcuts


@click.group("schema", help="Inspect CLI service metadata and shortcut contracts")
def schema_group() -> None:
    pass


@schema_group.command("list")
@click.argument("service", required=False)
@with_runtime_options(include_identity=False)
def schema_list(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    service_name = params.pop("service", None)
    if service_name:
        service = get_service(str(service_name))
        if service is None:
            shortcut_items = [item.schema_path for item in list_shortcuts(str(service_name))]
            cli_ctx.emit({"service": service_name, "methods": [], "shortcuts": shortcut_items})
            return
        payload = {
            "service": service.name,
            "description": service.description,
            "methods": sorted(method.cli_path for method in service.methods),
            "shortcuts": sorted(item.schema_path for item in list_shortcuts(service.name)),
        }
        cli_ctx.emit(payload)
        return
    cli_ctx.emit(
        {
            "version": load_metadata_snapshot().version,
            "services": [service.name for service in list_services()],
            "shortcuts": [item.schema_path for item in list_shortcuts()],
        }
    )


@schema_group.command("show")
@click.argument("schema_path")
@with_runtime_options(include_identity=False)
def schema_show(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    schema_path = str(params.pop("schema_path"))
    shortcut = get_shortcut(schema_path)
    if shortcut is not None:
        cli_ctx.emit(
            {
                "type": "shortcut",
                "schema_path": shortcut.schema_path,
                "service": shortcut.service,
                "name": shortcut.name,
                "description": shortcut.description,
                "risk": shortcut.risk,
                "supported_identities": list(shortcut.supported_identities),
                "example": f"feishu {shortcut.service} +{shortcut.name} --help",
            }
        )
        return
    method = find_method(schema_path)
    if method is None:
        raise ValueError(f"schema not found: {schema_path}")
    cli_ctx.emit(
        {
            "type": "service_method",
            "schema_path": method.cli_path,
            "id": method.id,
            "service": method.service,
            "resource": method.resource,
            "method": method.name,
            "http_method": method.http_method,
            "path": method.full_path,
            "description": method.description,
            "supported_identities": list(method.supported_identities),
            "scopes": list(method.scopes),
            "required_scopes": list(method.required_scopes),
            "doc_url": method.doc_url,
            "parameters": summarize_shape(method.parameters),
            "request_body": summarize_shape(method.request_body),
            "response_body": summarize_shape(method.response_body),
            "example": f"feishu {method.service} {method.resource} {method.name} --help",
        }
    )


@schema_group.command("paths")
@with_runtime_options(include_identity=False)
def schema_paths(**kwargs: Any) -> None:
    cli_ctx, _ = build_cli_context(kwargs)
    paths = list_schema_paths()
    cli_ctx.emit({"count": len(paths), "items": paths})


__all__ = ["schema_group"]
