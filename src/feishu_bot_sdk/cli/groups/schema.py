from __future__ import annotations

from typing import Any, Mapping

import click

from ..context import build_cli_context, with_runtime_options
from ..runtime.registry import (
    MethodSpec,
    ResourceSpec,
    ServiceSpec,
    find_method,
    get_service,
    list_schema_paths,
    list_services,
    load_metadata_snapshot,
    summarize_shape,
)
from ..shortcuts import get_shortcut, list_shortcuts


@click.command(
    "schema",
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
    help="Inspect CLI service metadata and shortcut contracts",
)
@click.argument("args", nargs=-1)
@with_runtime_options(include_identity=False)
@click.pass_context
def schema_group(ctx: click.Context, **kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    args = [str(item) for item in params.pop("args", ())]
    if args and args[0] in {"list", "show", "paths"}:
        _run_legacy_schema(cli_ctx, args)
        return
    path = args[0] if args else ""
    if len(args) > 1:
        raise ValueError("schema accepts at most one path")
    _run_lark_style_schema(cli_ctx, path)


def _run_legacy_schema(cli_ctx: Any, args: list[str]) -> None:
    command = args[0]
    values = args[1:]
    if command == "list":
        if len(values) > 1:
            raise ValueError("schema list accepts at most one service")
        _emit_legacy_list(cli_ctx, values[0] if values else None)
        return
    if command == "show":
        if len(values) != 1:
            raise ValueError("schema show requires a schema path")
        _emit_legacy_show(cli_ctx, values[0])
        return
    if command == "paths":
        if values:
            raise ValueError("schema paths does not accept arguments")
        paths = list_schema_paths()
        cli_ctx.emit({"count": len(paths), "items": paths})
        return
    raise ValueError(f"unknown schema command: {command}")


def _emit_legacy_list(cli_ctx: Any, service_name: str | None) -> None:
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


def _emit_legacy_show(cli_ctx: Any, schema_path: str) -> None:
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
    cli_ctx.emit(_legacy_method_payload(method))


def _run_lark_style_schema(cli_ctx: Any, path: str) -> None:
    output_format = cli_ctx.normalized_output_format()
    if not path:
        _emit_services(cli_ctx, output_format=output_format)
        return
    parts = [item.strip() for item in path.split(".") if item.strip()]
    if not parts:
        _emit_services(cli_ctx, output_format=output_format)
        return
    service = get_service(parts[0])
    if service is None:
        raise ValueError(f"Unknown service: {parts[0]}")
    if len(parts) == 1:
        _emit_service(cli_ctx, service, output_format=output_format)
        return
    resource, remaining = _find_resource_by_path(service, parts[1:])
    if resource is None:
        raise ValueError(f"Unknown resource: {path}")
    if not remaining:
        _emit_resource(cli_ctx, service, resource, output_format=output_format)
        return
    if len(remaining) > 1:
        raise ValueError(f"Unknown method: {path}")
    method_name = remaining[0]
    method = next((item for item in resource.methods if item.name == method_name), None)
    if method is None:
        raise ValueError(f"Unknown method: {path}")
    _emit_method(cli_ctx, service, resource, method, output_format=output_format)


def _emit_services(cli_ctx: Any, *, output_format: str) -> None:
    if output_format == "pretty":
        payload = {
            "services": [
                {
                    "name": service.name,
                    "title": service.title,
                    "description": service.description,
                }
                for service in list_services()
            ],
            "usage": "feishu schema <service>.<resource>.<method>",
        }
        cli_ctx.emit(payload)
        return
    cli_ctx.emit(
        {
            "version": load_metadata_snapshot().version,
            "source": load_metadata_snapshot().source,
            "source_commit": load_metadata_snapshot().source_commit,
            "services": [service.name for service in list_services()],
        }
    )


def _emit_service(cli_ctx: Any, service: ServiceSpec, *, output_format: str) -> None:
    if output_format == "pretty":
        payload = {
            "service": service.name,
            "version": service.version,
            "title": service.title,
            "base_path": service.service_path,
            "resources": [
                {
                    "name": resource.name,
                    "methods": [method.name for method in resource.methods],
                }
                for resource in service.resources
            ],
            "usage": f"feishu schema {service.name}.<resource>.<method>",
        }
        cli_ctx.emit(payload)
        return
    cli_ctx.emit(service.raw)


def _emit_resource(
    cli_ctx: Any,
    service: ServiceSpec,
    resource: ResourceSpec,
    *,
    output_format: str,
) -> None:
    if output_format == "pretty":
        payload = {
            "resource": f"{service.name}.{resource.name}",
            "methods": [
                {
                    "name": method.name,
                    "http_method": method.http_method,
                    "description": method.description,
                }
                for method in resource.methods
            ],
            "usage": f"feishu schema {service.name}.{resource.name}.<method>",
        }
        cli_ctx.emit(payload)
        return
    cli_ctx.emit(resource.raw)


def _emit_method(
    cli_ctx: Any,
    service: ServiceSpec,
    resource: ResourceSpec,
    method: MethodSpec,
    *,
    output_format: str,
) -> None:
    if output_format == "pretty":
        cli_ctx.emit(_pretty_method_payload(service, resource, method))
        return
    cli_ctx.emit(method.raw)


def _find_resource_by_path(
    service: ServiceSpec,
    parts: list[str],
) -> tuple[ResourceSpec | None, list[str]]:
    for index in range(len(parts), 0, -1):
        candidate = ".".join(parts[:index])
        for resource in service.resources:
            if resource.name == candidate:
                return resource, parts[index:]
    return None, []


def _legacy_method_payload(method: MethodSpec) -> dict[str, Any]:
    return {
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


def _pretty_method_payload(
    service: ServiceSpec,
    resource: ResourceSpec,
    method: MethodSpec,
) -> dict[str, Any]:
    file_fields = _detect_file_fields(method.request_body)
    payload: dict[str, Any] = {
        "schema_path": method.cli_path,
        "http_method": method.http_method,
        "path": method.full_path,
        "description": method.description,
        "parameters": _summarize_fields(method.parameters),
        "request_body": _summarize_fields(method.request_body),
        "response_body": _summarize_fields(method.response_body),
        "identity": list(method.supported_identities),
        "scopes": list(method.scopes),
        "cli": f"feishu {service.name} {resource.name} {method.name}",
        "doc_url": method.doc_url,
    }
    if file_fields:
        file_arg = "<path>" if len(file_fields) == 1 else "<field=path>"
        payload["file_upload"] = {
            "enabled": True,
            "fields": file_fields,
            "default_field": file_fields[0] if len(file_fields) == 1 else None,
            "flag": f"--file {file_arg}",
            "notice": (
                f'file upload; Default field: "{file_fields[0]}"'
                if len(file_fields) == 1
                else f"file upload; Fields: {', '.join(file_fields)}"
            ),
        }
        payload["cli"] = f"{payload['cli']} --file {file_arg}"
    return payload


def _summarize_fields(fields: Mapping[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for name, raw in sorted(fields.items(), key=lambda item: _field_sort_key(item[0], item[1])):
        if not isinstance(raw, Mapping):
            continue
        item = {
            "name": str(name),
            "type": raw.get("type") or "string",
            "location": raw.get("location"),
            "required": bool(raw.get("required")),
            "description": raw.get("description") or "",
        }
        options = raw.get("options") or raw.get("enum")
        if isinstance(options, list):
            item["options"] = _option_values(options)
        properties = raw.get("properties")
        if isinstance(properties, Mapping):
            item["properties"] = _summarize_fields(properties)
        result.append(item)
    return result


def _field_sort_key(name: str, raw: Any) -> tuple[int, str]:
    required = bool(raw.get("required")) if isinstance(raw, Mapping) else False
    return (0 if required else 1, name)


def _option_values(options: list[Any]) -> list[Any]:
    values: list[Any] = []
    for option in options:
        if isinstance(option, Mapping) and "value" in option:
            values.append(option["value"])
        else:
            values.append(option)
    return values


def _detect_file_fields(fields: Mapping[str, Any], *, prefix: str = "") -> list[str]:
    result: list[str] = []
    for name, raw in fields.items():
        if not isinstance(raw, Mapping):
            continue
        field_name = f"{prefix}.{name}" if prefix else str(name)
        if raw.get("type") == "file":
            result.append(field_name)
        properties = raw.get("properties")
        if isinstance(properties, Mapping):
            result.extend(_detect_file_fields(properties, prefix=field_name))
    return result


__all__ = ["schema_group"]
