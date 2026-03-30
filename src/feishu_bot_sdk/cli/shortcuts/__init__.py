from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import click

from ..commands.content import (
    _cmd_bitable_create_from_csv,
    _cmd_docx_convert_content,
    _cmd_docx_insert_content,
    _cmd_drive_requester_upload_file,
)
from ..commands.mail import _cmd_message_send_markdown
from ..commands.org import _cmd_calendar_attach_material
from ..context import CLIContext, build_cli_context, with_runtime_options
from ..runtime.identity import identity_to_auth_mode, resolve_identity


ShortcutCallback = Callable[[CLIContext, dict[str, Any]], Any]


@dataclass(frozen=True)
class ShortcutSpec:
    service: str
    name: str
    description: str
    risk: str
    supported_identities: tuple[str, ...]
    command_factory: Callable[[], click.Command]

    @property
    def schema_path(self) -> str:
        return f"{self.service}.+{self.name}"


def list_shortcuts(service: str | None = None) -> list[ShortcutSpec]:
    items = [
        ShortcutSpec(
            service="bitable",
            name="create-from-csv",
            description="Create a new Bitable app and initial table from a CSV file",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=_bitable_create_from_csv_command,
        ),
        ShortcutSpec(
            service="docx",
            name="convert-content",
            description="Convert markdown/html/text into Docx block payloads",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=_docx_convert_content_command,
        ),
        ShortcutSpec(
            service="docx",
            name="insert-content",
            description="Convert content and insert it into a Docx document",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=_docx_insert_content_command,
        ),
        ShortcutSpec(
            service="calendar",
            name="attach-material",
            description="Upload a file and attach it to a calendar event",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=_calendar_attach_material_command,
        ),
        ShortcutSpec(
            service="drive",
            name="requester-upload",
            description="Create a fresh child folder under requester root, upload, and verify owner",
            risk="write",
            supported_identities=("user",),
            command_factory=_drive_requester_upload_command,
        ),
        ShortcutSpec(
            service="mail",
            name="send-markdown",
            description="Render markdown and send it as an email message",
            risk="write",
            supported_identities=("user", "bot"),
            command_factory=_mail_send_markdown_command,
        ),
    ]
    if service is None:
        return items
    return [item for item in items if item.service == service]


def get_shortcut(schema_path: str) -> ShortcutSpec | None:
    normalized = str(schema_path or "").strip()
    for shortcut in list_shortcuts():
        if shortcut.schema_path == normalized:
            return shortcut
    return None


def attach_shortcuts(group: click.Group, service: str) -> None:
    for spec in list_shortcuts(service):
        command_name = f"+{spec.name}"
        if command_name in group.commands:
            continue
        group.add_command(spec.command_factory())


def _shortcut_dry_run_payload(
    *,
    shortcut: ShortcutSpec,
    identity: str,
    params: dict[str, Any],
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "ok": True,
        "dry_run": True,
        "type": "shortcut",
        "shortcut": shortcut.schema_path,
        "risk": shortcut.risk,
        "identity": identity,
        "params": params,
        "steps": steps,
    }


def _invoke_shortcut(
    *,
    cli_ctx: CLIContext,
    shortcut: ShortcutSpec,
    handler: Callable[[Any], Any],
    params: dict[str, Any],
    dry_run: bool,
    group: str,
    command_field: str,
    command_name: str,
    steps: list[dict[str, Any]],
) -> None:
    identity = resolve_identity(cli_ctx, shortcut.supported_identities)
    if dry_run:
        cli_ctx.emit(
            _shortcut_dry_run_payload(
                shortcut=shortcut,
                identity=identity.identity,
                params=params,
                steps=steps,
            )
        )
        return
    args = cli_ctx.build_args(
        group=group,
        auth_mode=identity_to_auth_mode(identity.identity),
        **{command_field: command_name},
        **params,
    )
    result = handler(args)
    cli_ctx.emit(result, cli_args=args)


def _bitable_create_from_csv_command() -> click.Command:
    spec = get_shortcut("bitable.+create-from-csv")
    assert spec is not None

    @click.command(name="+create-from-csv", help=spec.description)
    @click.argument("csv_path")
    @click.option("--app-name", required=True)
    @click.option("--table-name", required=True)
    @click.option("--grant-member-id")
    @click.option("--member-id-type", default="open_id", show_default=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_bitable_create_from_csv,
            params=params,
            dry_run=dry_run,
            group="bitable",
            command_field="bitable_command",
            command_name="create-from-csv",
            steps=[
                {"action": "bitable.create_from_csv", "uses": ["bitable app create", "table bootstrap", "optional permission grant"]},
            ],
        )

    return _command


def _docx_convert_content_command() -> click.Command:
    spec = get_shortcut("docx.+convert-content")
    assert spec is not None

    @click.command(name="+convert-content", help=spec.description)
    @click.option("--content")
    @click.option("--content-file")
    @click.option("--content-stdin", is_flag=True)
    @click.option("--content-type", default="markdown", show_default=True)
    @click.option("--output")
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_docx_convert_content,
            params=params,
            dry_run=dry_run,
            group="docx",
            command_field="docx_command",
            command_name="convert-content",
            steps=[{"action": "docx.blocks.convert_content"}],
        )

    return _command


def _docx_insert_content_command() -> click.Command:
    spec = get_shortcut("docx.+insert-content")
    assert spec is not None

    @click.command(name="+insert-content", help=spec.description)
    @click.option("--document-id", required=True)
    @click.option("--block-id")
    @click.option("--content")
    @click.option("--content-file")
    @click.option("--content-stdin", is_flag=True)
    @click.option("--content-type", default="markdown", show_default=True)
    @click.option("--index", type=int, default=-1, show_default=True)
    @click.option("--document-revision-id")
    @click.option("--client-token")
    @click.option("--user-id-type")
    @click.option("--full-response", is_flag=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_docx_insert_content,
            params=params,
            dry_run=dry_run,
            group="docx",
            command_field="docx_command",
            command_name="insert-content",
            steps=[
                {"action": "docx.blocks.convert_content"},
                {"action": "docx.document.insert_content"},
            ],
        )

    return _command


def _calendar_attach_material_command() -> click.Command:
    spec = get_shortcut("calendar.+attach-material")
    assert spec is not None

    @click.command(name="+attach-material", help=spec.description)
    @click.argument("path")
    @click.option("--calendar-id", required=True)
    @click.option("--event-id", required=True)
    @click.option("--mode", default="append", show_default=True)
    @click.option("--file-name")
    @click.option("--content-type")
    @click.option("--need-notification")
    @click.option("--user-id-type")
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_calendar_attach_material,
            params=params,
            dry_run=dry_run,
            group="calendar",
            command_field="calendar_command",
            command_name="attach-material",
            steps=[
                {"action": "drive.media.upload", "parent_type": "calendar"},
                {"action": "calendar.events.update"},
            ],
        )

    return _command


def _drive_requester_upload_command() -> click.Command:
    spec = get_shortcut("drive.+requester-upload")
    assert spec is not None

    @click.command(name="+requester-upload", help=spec.description)
    @click.argument("path")
    @click.option("--folder-name")
    @click.option("--file-name")
    @click.option("--checksum")
    @click.option("--content-type")
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_drive_requester_upload_file,
            params=params,
            dry_run=dry_run,
            group="drive",
            command_field="drive_command",
            command_name="requester-upload-file",
            steps=[
                {"action": "drive.root_folder_meta", "identity": "user"},
                {"action": "drive.create_folder", "parent": "requester_root"},
                {"action": "drive.upload_file", "parent_type": "explorer"},
                {"action": "drive.files.meta", "verify": "requester_owner"},
            ],
        )

    return _command


def _mail_send_markdown_command() -> click.Command:
    spec = get_shortcut("mail.+send-markdown")
    assert spec is not None

    @click.command(name="+send-markdown", help=spec.description)
    @click.option("--user-mailbox-id", required=True)
    @click.option("--to-email", "to_emails", multiple=True)
    @click.option("--cc-email", "cc_emails", multiple=True)
    @click.option("--bcc-email", "bcc_emails", multiple=True)
    @click.option("--to-json")
    @click.option("--cc-json")
    @click.option("--bcc-json")
    @click.option("--subject")
    @click.option("--markdown")
    @click.option("--markdown-file")
    @click.option("--markdown-stdin", is_flag=True)
    @click.option("--base-dir")
    @click.option("--head-from-name")
    @click.option("--dedupe-key")
    @click.option("--latex-mode", default="auto", show_default=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_message_send_markdown,
            params=params,
            dry_run=dry_run,
            group="mail",
            command_field="mail_command",
            command_name="send-markdown",
            steps=[
                {"action": "mail.markdown.render"},
                {"action": "mail.messages.send"},
            ],
        )

    return _command


__all__ = [
    "ShortcutSpec",
    "attach_shortcuts",
    "get_shortcut",
    "list_shortcuts",
]
