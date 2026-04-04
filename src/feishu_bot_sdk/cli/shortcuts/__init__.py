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
from ..commands.drive_shortcuts import (
    _cmd_drive_export_shortcut,
    _cmd_drive_import_shortcut,
    _cmd_drive_move_shortcut,
    _cmd_drive_task_result_shortcut,
)
from ..commands.mail import _cmd_message_send_markdown
from ..commands.mail_shortcuts import (
    _cmd_mail_draft_create,
    _cmd_mail_draft_edit,
    _cmd_mail_thread,
)
from ..commands.minutes import _cmd_minutes_download
from ..commands.org import _cmd_calendar_attach_material, _cmd_calendar_rsvp
from ..commands.task_shortcuts import (
    _cmd_task_assign_shortcut,
    _cmd_task_comment_shortcut,
    _cmd_task_complete_shortcut,
    _cmd_task_create_shortcut,
    _cmd_task_delete_shortcut,
    _cmd_task_followers_shortcut,
    _cmd_task_get_my_tasks_shortcut,
    _cmd_task_reminder_shortcut,
    _cmd_task_reopen_shortcut,
)
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
            service="minutes",
            name="download",
            description="Download minute media or print the temporary download URL",
            risk="read",
            supported_identities=("bot", "user"),
            command_factory=_minutes_download_command,
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
            service="calendar",
            name="rsvp",
            description="Reply to a calendar event with accept, decline or tentative",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=_calendar_rsvp_command,
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
            service="drive",
            name="import",
            description="Upload a local file and create a Drive import task",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=_drive_import_command,
        ),
        ShortcutSpec(
            service="drive",
            name="export",
            description="Export a Drive-native file to the local filesystem",
            risk="read",
            supported_identities=("bot", "user"),
            command_factory=_drive_export_command,
        ),
        ShortcutSpec(
            service="drive",
            name="move",
            description="Move a Drive file or folder and poll async folder tasks",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=_drive_move_command,
        ),
        ShortcutSpec(
            service="drive",
            name="task_result",
            description="Query async Drive import, export, or task-check results",
            risk="read",
            supported_identities=("bot", "user"),
            command_factory=_drive_task_result_command,
        ),
        ShortcutSpec(
            service="task",
            name="create",
            description="Create a task from shortcut-style flags",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=_task_create_command,
        ),
        ShortcutSpec(
            service="task",
            name="comment",
            description="Add a comment to a task",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=_task_comment_command,
        ),
        ShortcutSpec(
            service="task",
            name="delete",
            description="Delete a task by guid",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=_task_delete_command,
        ),
        ShortcutSpec(
            service="task",
            name="complete",
            description="Mark a task as completed, skipping PATCH when already complete",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=_task_complete_command,
        ),
        ShortcutSpec(
            service="task",
            name="reopen",
            description="Reopen a completed task",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=_task_reopen_command,
        ),
        ShortcutSpec(
            service="task",
            name="assign",
            description="Add or remove assignees on a task",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=_task_assign_command,
        ),
        ShortcutSpec(
            service="task",
            name="followers",
            description="Add or remove followers on a task",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=_task_followers_command,
        ),
        ShortcutSpec(
            service="task",
            name="reminder",
            description="Set or clear task reminders",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=_task_reminder_command,
        ),
        ShortcutSpec(
            service="task",
            name="get-my-tasks",
            description="List tasks assigned to the current user with client-side filtering",
            risk="read",
            supported_identities=("user",),
            command_factory=_task_get_my_tasks_command,
        ),
        ShortcutSpec(
            service="mail",
            name="send-markdown",
            description="Render markdown and send it as an email message",
            risk="write",
            supported_identities=("user", "bot"),
            command_factory=_mail_send_markdown_command,
        ),
        ShortcutSpec(
            service="mail",
            name="draft-create",
            description="Create a new mail draft from raw EML content",
            risk="write",
            supported_identities=("user",),
            command_factory=_mail_draft_create_command,
        ),
        ShortcutSpec(
            service="mail",
            name="draft-edit",
            description="Replace an existing draft with new raw EML content",
            risk="write",
            supported_identities=("user",),
            command_factory=_mail_draft_edit_command,
        ),
        ShortcutSpec(
            service="mail",
            name="thread",
            description="Fetch a mail thread with selectable detail level",
            risk="read",
            supported_identities=("user", "bot"),
            command_factory=_mail_thread_command,
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


def _minutes_download_command() -> click.Command:
    spec = get_shortcut("minutes.+download")
    assert spec is not None

    @click.command(name="+download", help=spec.description)
    @click.option("--minute-tokens", required=True)
    @click.option("--output")
    @click.option("--overwrite", is_flag=True)
    @click.option("--url-only", is_flag=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_minutes_download,
            params=params,
            dry_run=dry_run,
            group="minutes",
            command_field="minutes_command",
            command_name="download",
            steps=[
                {"action": "minutes.media.get_download_url"},
                {"action": "minutes.media.download", "optional": True},
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


def _calendar_rsvp_command() -> click.Command:
    spec = get_shortcut("calendar.+rsvp")
    assert spec is not None

    @click.command(name="+rsvp", help=spec.description)
    @click.option("--calendar-id")
    @click.option("--event-id", required=True)
    @click.option(
        "--rsvp-status",
        type=click.Choice(["accept", "decline", "tentative"]),
        required=True,
    )
    @click.option("--user-id-type")
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_calendar_rsvp,
            params=params,
            dry_run=dry_run,
            group="calendar",
            command_field="calendar_command",
            command_name="rsvp",
            steps=[
                {"action": "calendar.primary", "optional": True},
                {"action": "calendar.events.reply"},
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


def _drive_import_command() -> click.Command:
    spec = get_shortcut("drive.+import")
    assert spec is not None

    @click.command(name="+import", help=spec.description)
    @click.option("--file", "file_path", required=True)
    @click.option("--type", required=True)
    @click.option("--folder-token")
    @click.option("--name")
    @click.option("--poll-attempts", type=int, default=6, show_default=True)
    @click.option("--poll-interval", type=float, default=2.0, show_default=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_drive_import_shortcut,
            params=params,
            dry_run=dry_run,
            group="drive",
            command_field="drive_command",
            command_name="import",
            steps=[
                {"action": "drive.media.upload", "parent_type": "ccm_import_open"},
                {"action": "drive.import_tasks.create"},
                {"action": "drive.import_tasks.poll", "optional": True},
            ],
        )

    return _command


def _drive_export_command() -> click.Command:
    spec = get_shortcut("drive.+export")
    assert spec is not None

    @click.command(name="+export", help=spec.description)
    @click.option("--token", required=True)
    @click.option("--doc-type", required=True)
    @click.option("--file-extension", required=True)
    @click.option("--sub-id")
    @click.option("--output-dir", default=".", show_default=True)
    @click.option("--overwrite", is_flag=True)
    @click.option("--poll-attempts", type=int, default=6, show_default=True)
    @click.option("--poll-interval", type=float, default=2.0, show_default=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_drive_export_shortcut,
            params=params,
            dry_run=dry_run,
            group="drive",
            command_field="drive_command",
            command_name="export",
            steps=[
                {"action": "drive.export_tasks.create", "optional": True},
                {"action": "drive.export_tasks.poll", "optional": True},
                {"action": "drive.export_tasks.download", "optional": True},
            ],
        )

    return _command


def _drive_move_command() -> click.Command:
    spec = get_shortcut("drive.+move")
    assert spec is not None

    @click.command(name="+move", help=spec.description)
    @click.option("--file-token", required=True)
    @click.option("--type", required=True)
    @click.option("--folder-token")
    @click.option("--poll-attempts", type=int, default=6, show_default=True)
    @click.option("--poll-interval", type=float, default=2.0, show_default=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_drive_move_shortcut,
            params=params,
            dry_run=dry_run,
            group="drive",
            command_field="drive_command",
            command_name="move",
            steps=[
                {"action": "drive.root_folder_meta", "optional": True},
                {"action": "drive.files.move"},
                {"action": "drive.files.task_check", "optional": True},
            ],
        )

    return _command


def _drive_task_result_command() -> click.Command:
    spec = get_shortcut("drive.+task_result")
    assert spec is not None

    @click.command(name="+task_result", help=spec.description)
    @click.option(
        "--scenario",
        type=click.Choice(["import", "export", "task_check"]),
        required=True,
    )
    @click.option("--ticket")
    @click.option("--task-id")
    @click.option("--file-token")
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_drive_task_result_shortcut,
            params=params,
            dry_run=dry_run,
            group="drive",
            command_field="drive_command",
            command_name="task-result",
            steps=[{"action": "drive.tasks.query"}],
        )

    return _command


def _task_create_command() -> click.Command:
    spec = get_shortcut("task.+create")
    assert spec is not None

    @click.command(name="+create", help=spec.description)
    @click.option("--summary")
    @click.option("--description")
    @click.option("--assignee")
    @click.option("--due")
    @click.option("--tasklist-id")
    @click.option("--idempotency-key")
    @click.option("--data")
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_task_create_shortcut,
            params=params,
            dry_run=dry_run,
            group="task",
            command_field="task_command",
            command_name="create",
            steps=[{"action": "task.tasks.create"}],
        )

    return _command


def _task_comment_command() -> click.Command:
    spec = get_shortcut("task.+comment")
    assert spec is not None

    @click.command(name="+comment", help=spec.description)
    @click.option("--task-id", required=True)
    @click.option("--content", required=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_task_comment_shortcut,
            params=params,
            dry_run=dry_run,
            group="task",
            command_field="task_command",
            command_name="comment",
            steps=[{"action": "task.comments.create"}],
        )

    return _command


def _task_delete_command() -> click.Command:
    spec = get_shortcut("task.+delete")
    assert spec is not None

    @click.command(name="+delete", help=spec.description)
    @click.option("--task-id", required=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_task_delete_shortcut,
            params=params,
            dry_run=dry_run,
            group="task",
            command_field="task_command",
            command_name="delete",
            steps=[{"action": "task.tasks.delete"}],
        )

    return _command


def _task_complete_command() -> click.Command:
    spec = get_shortcut("task.+complete")
    assert spec is not None

    @click.command(name="+complete", help=spec.description)
    @click.option("--task-id", required=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_task_complete_shortcut,
            params=params,
            dry_run=dry_run,
            group="task",
            command_field="task_command",
            command_name="complete",
            steps=[
                {"action": "task.tasks.get"},
                {"action": "task.tasks.patch_if_needed"},
            ],
        )

    return _command


def _task_reopen_command() -> click.Command:
    spec = get_shortcut("task.+reopen")
    assert spec is not None

    @click.command(name="+reopen", help=spec.description)
    @click.option("--task-id", required=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_task_reopen_shortcut,
            params=params,
            dry_run=dry_run,
            group="task",
            command_field="task_command",
            command_name="reopen",
            steps=[{"action": "task.tasks.patch"}],
        )

    return _command


def _task_assign_command() -> click.Command:
    spec = get_shortcut("task.+assign")
    assert spec is not None

    @click.command(name="+assign", help=spec.description)
    @click.option("--task-id", required=True)
    @click.option("--add")
    @click.option("--remove")
    @click.option("--idempotency-key")
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_task_assign_shortcut,
            params=params,
            dry_run=dry_run,
            group="task",
            command_field="task_command",
            command_name="assign",
            steps=[
                {"action": "task.members.add_or_remove", "role": "assignee"},
            ],
        )

    return _command


def _task_followers_command() -> click.Command:
    spec = get_shortcut("task.+followers")
    assert spec is not None

    @click.command(name="+followers", help=spec.description)
    @click.option("--task-id", required=True)
    @click.option("--add")
    @click.option("--remove")
    @click.option("--idempotency-key")
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_task_followers_shortcut,
            params=params,
            dry_run=dry_run,
            group="task",
            command_field="task_command",
            command_name="followers",
            steps=[
                {"action": "task.members.add_or_remove", "role": "follower"},
            ],
        )

    return _command


def _task_reminder_command() -> click.Command:
    spec = get_shortcut("task.+reminder")
    assert spec is not None

    @click.command(name="+reminder", help=spec.description)
    @click.option("--task-id", required=True)
    @click.option("--set")
    @click.option("--remove", is_flag=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_task_reminder_shortcut,
            params=params,
            dry_run=dry_run,
            group="task",
            command_field="task_command",
            command_name="reminder",
            steps=[
                {"action": "task.tasks.get"},
                {"action": "task.reminders.replace"},
            ],
        )

    return _command


def _task_get_my_tasks_command() -> click.Command:
    spec = get_shortcut("task.+get-my-tasks")
    assert spec is not None

    @click.command(name="+get-my-tasks", help=spec.description)
    @click.option("--query")
    @click.option("--complete", is_flag=True)
    @click.option("--created-at")
    @click.option("--due-start")
    @click.option("--due-end")
    @click.option("--page-all", is_flag=True)
    @click.option("--page-limit", type=int, default=20, show_default=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_task_get_my_tasks_shortcut,
            params=params,
            dry_run=dry_run,
            group="task",
            command_field="task_command",
            command_name="get-my-tasks",
            steps=[
                {"action": "task.tasks.list", "type": "my_tasks"},
                {"action": "task.tasks.filter_client_side"},
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


def _mail_draft_create_command() -> click.Command:
    spec = get_shortcut("mail.+draft-create")
    assert spec is not None

    @click.command(name="+draft-create", help=spec.description)
    @click.option("--user-mailbox-id", required=True)
    @click.option("--raw")
    @click.option("--raw-file")
    @click.option("--raw-stdin", is_flag=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_mail_draft_create,
            params=params,
            dry_run=dry_run,
            group="mail",
            command_field="mail_command",
            command_name="draft-create",
            steps=[{"action": "mail.drafts.create"}],
        )

    return _command


def _mail_draft_edit_command() -> click.Command:
    spec = get_shortcut("mail.+draft-edit")
    assert spec is not None

    @click.command(name="+draft-edit", help=spec.description)
    @click.option("--user-mailbox-id", required=True)
    @click.option("--draft-id", required=True)
    @click.option("--raw")
    @click.option("--raw-file")
    @click.option("--raw-stdin", is_flag=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_mail_draft_edit,
            params=params,
            dry_run=dry_run,
            group="mail",
            command_field="mail_command",
            command_name="draft-edit",
            steps=[{"action": "mail.drafts.update"}],
        )

    return _command


def _mail_thread_command() -> click.Command:
    spec = get_shortcut("mail.+thread")
    assert spec is not None

    @click.command(name="+thread", help=spec.description)
    @click.option("--user-mailbox-id", required=True)
    @click.option("--thread-id", required=True)
    @click.option(
        "--thread-format",
        type=click.Choice(["full", "plain_text_full", "metadata"]),
        default="full",
        show_default=True,
    )
    @click.option("--include-spam-trash", is_flag=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_mail_thread,
            params=params,
            dry_run=dry_run,
            group="mail",
            command_field="mail_command",
            command_name="thread",
            steps=[{"action": "mail.threads.get"}],
        )

    return _command


__all__ = [
    "ShortcutSpec",
    "attach_shortcuts",
    "get_shortcut",
    "list_shortcuts",
]
