from __future__ import annotations

from typing import Any

import click

from ..context import build_cli_context, with_runtime_options, with_service_io_options
from ..runtime import _build_client, _normalize_path, _parse_json_object, build_multipart_file
from ..runtime.identity import identity_to_auth_mode, resolve_identity


@click.command("api", help="Generic raw OpenAPI call")
@click.argument("method")
@click.argument("path")
@with_service_io_options
@with_runtime_options
def api_command(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    method = str(params.pop("method"))
    path = _normalize_path(str(params.pop("path")))
    resolution = resolve_identity(cli_ctx)
    params_payload = _parse_json_object(
        json_text=params.pop("params", None),
        file_path=None,
        stdin_enabled=False,
        name="params",
        required=False,
    )
    data_payload = _parse_json_object(
        json_text=params.pop("data", None),
        file_path=None,
        stdin_enabled=False,
        name="data",
        required=False,
    )
    page_all = bool(params.pop("page_all", False))
    dry_run = bool(params.pop("dry_run", False))
    semantic_output = params.pop("output", None)
    params.pop("page_size", None)
    params.pop("page_limit", None)
    params.pop("page_delay", None)
    params.pop("yes", None)
    file_upload = params.pop("file_upload", None)
    file_field: str | None = None
    file_payload: tuple[str, bytes, str] | None = None
    file_meta: dict[str, str] | None = None
    if file_upload:
        file_field, file_payload, file_meta = build_multipart_file(str(file_upload))
    if page_all and semantic_output:
        raise ValueError("--output and --page-all are mutually exclusive")
    if dry_run:
        cli_ctx.emit(
            {
                "ok": True,
                "dry_run": True,
                "type": "api",
                "identity": resolution.identity,
                "request": {
                    "method": method.upper(),
                    "path": path,
                    "params": params_payload or None,
                    "data": data_payload or None,
                    "file": file_meta,
                    "output": semantic_output,
                },
            }
        )
        return
    args = cli_ctx.build_args(group="api", auth_mode=identity_to_auth_mode(resolution.identity))
    client = _build_client(args)
    if file_field is not None and file_payload is not None:
        result = client.request_multipart(
            method,
            path,
            params=params_payload or None,
            data=data_payload or None,
            files={file_field: file_payload},
        )
    else:
        result = client.request_json(method, path, params=params_payload or None, payload=data_payload or None)
    if semantic_output:
        from pathlib import Path
        import json

        target = Path(str(semantic_output))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        cli_ctx.emit({"ok": True, "output": str(target), "path": path, "method": method.upper()}, cli_args=args)
        return
    cli_ctx.emit(result, cli_args=args)


__all__ = ["api_command"]
