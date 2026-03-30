from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

import click

from ..context import build_cli_context, with_runtime_options, with_service_io_options
from ..runtime import _build_client, _parse_json_object
from ..runtime.identity import identity_to_auth_mode, resolve_identity
from ..runtime.registry import MethodSpec, ServiceSpec, list_services
from ..shortcuts import attach_shortcuts


_PATH_PARAM_PATTERN = re.compile(r"{([^{}]+)}")


def register_service_groups(root: click.Group) -> None:
    for service in list_services():
        existing = root.commands.get(service.name)
        if isinstance(existing, click.Group):
            _merge_service_group(existing, service)
            continue
        root.add_command(_build_service_group(service))


def _build_service_group(service: ServiceSpec) -> click.Group:
    help_text = service.description or service.title
    if service.name == "mail":
        help_text = f"{help_text}\n\nKey areas: mailbox, message, group, public-mailbox, contact, rule."
    group = click.Group(service.name, help=help_text)
    for resource in service.resources:
        resource_group = click.Group(resource.name, help=f"{resource.name} operations")
        for method in resource.methods:
            resource_group.add_command(_build_method_command(method))
        group.add_command(resource_group)
    attach_shortcuts(group, service.name)
    return group


def _merge_service_group(group: click.Group, service: ServiceSpec) -> None:
    if not group.help or group.help.endswith("shortcuts"):
        group.help = service.description or service.title or group.help
    for resource in service.resources:
        existing = group.commands.get(resource.name)
        if isinstance(existing, click.Group):
            resource_group = existing
        else:
            resource_group = click.Group(resource.name, help=f"{resource.name} operations")
            group.add_command(resource_group)
        for method in resource.methods:
            if method.name not in resource_group.commands:
                resource_group.add_command(_build_method_command(method))
    attach_shortcuts(group, service.name)


def _build_method_command(method: MethodSpec) -> click.Command:
    help_text = method.description or f"{method.http_method} {method.full_path}"

    @click.command(name=method.name, help=help_text)
    @with_service_io_options
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        resolution = resolve_identity(cli_ctx, method.supported_identities)
        raw_params = _parse_json_object(
            json_text=params.pop("params", None),
            file_path=None,
            stdin_enabled=False,
            name="params",
            required=False,
        )
        raw_data = _parse_json_object(
            json_text=params.pop("data", None),
            file_path=None,
            stdin_enabled=False,
            name="data",
            required=False,
        )
        page_all = bool(params.pop("page_all", False))
        page_size = params.pop("page_size", None)
        page_limit = int(params.pop("page_limit", 10))
        page_delay = int(params.pop("page_delay", 200))
        dry_run = bool(params.pop("dry_run", False))
        output_path = params.pop("output", None)
        effective_params = dict(raw_params or {})
        if page_size is not None and "page_size" not in effective_params:
            effective_params["page_size"] = page_size
        resolved_path, query_params = _render_path(method, effective_params)
        if dry_run:
            cli_ctx.emit(
                {
                    "ok": True,
                    "dry_run": True,
                    "type": "service_method",
                    "schema_path": method.cli_path,
                    "identity": resolution.identity,
                    "request": {
                        "http_method": method.http_method,
                        "path": resolved_path,
                        "params": query_params or None,
                        "data": raw_data or None,
                        "output": output_path,
                    },
                    "risk": "high-risk-write" if method.danger else ("write" if method.http_method != "GET" else "read"),
                }
            )
            return
        args = cli_ctx.build_args(group=method.service, auth_mode=identity_to_auth_mode(resolution.identity))
        client = _build_client(args)
        if page_all:
            result = _paginate(client, method, resolved_path, query_params, raw_data, page_limit=page_limit, page_delay=page_delay)
        else:
            result = client.request_json(method.http_method, resolved_path, params=query_params or None, payload=raw_data or None)
        if output_path:
            target = Path(str(output_path))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            cli_ctx.emit({"ok": True, "output": str(target), "schema_path": method.cli_path}, cli_args=args)
            return
        cli_ctx.emit(result, cli_args=args)

    return _command


def _render_path(method: MethodSpec, params: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    query_params = dict(params)
    path = method.full_path
    for match in _PATH_PARAM_PATTERN.findall(path):
        if match not in query_params:
            raise ValueError(f"missing path parameter {match!r}; pass it inside --params JSON")
        value = str(query_params.pop(match))
        path = path.replace("{" + match + "}", value)
    return path, query_params


def _paginate(
    client: Any,
    method: MethodSpec,
    resolved_path: str,
    query_params: dict[str, Any],
    data: dict[str, Any] | None,
    *,
    page_limit: int,
    page_delay: int,
) -> dict[str, Any]:
    current_params = dict(query_params)
    current_data = dict(data or {})
    items: list[Any] = []
    pages = 0
    last_payload: dict[str, Any] | None = None
    while True:
        pages += 1
        if page_limit and pages > page_limit:
            break
        payload = client.request_json(method.http_method, resolved_path, params=current_params or None, payload=current_data or None)
        last_payload = payload
        data_payload = payload.get("data") if isinstance(payload, dict) and isinstance(payload.get("data"), dict) else payload
        batch = data_payload.get("items") if isinstance(data_payload, dict) else None
        if isinstance(batch, list):
            items.extend(batch)
        has_more = bool(isinstance(data_payload, dict) and data_payload.get("has_more"))
        page_token = data_payload.get("page_token") if isinstance(data_payload, dict) else None
        if not has_more or not isinstance(page_token, str) or not page_token:
            break
        current_params["page_token"] = page_token
        _sleep_between_pages(page_delay)
    if last_payload is None:
        return {"items": [], "count": 0}
    result = dict(last_payload)
    data_payload = result.get("data")
    if isinstance(data_payload, dict):
        data_payload = dict(data_payload)
        data_payload["items"] = items
        data_payload["count"] = len(items)
        data_payload["has_more"] = False
        result["data"] = data_payload
        return result
    result["items"] = items
    result["count"] = len(items)
    return result


def _sleep_between_pages(page_delay: int) -> None:
    remaining_seconds = max(page_delay, 0) / 1000.0
    while remaining_seconds > 0:
        interval = min(remaining_seconds, 0.1)
        time.sleep(interval)
        remaining_seconds -= interval


__all__ = ["register_service_groups"]
