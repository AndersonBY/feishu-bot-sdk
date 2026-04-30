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
from ..commands.base_shortcuts import BASE_SHORTCUT_NAMES, _cmd_base_shortcut
from ..commands.contact_shortcuts import (
    _cmd_contact_get_user,
    _cmd_contact_search_user,
)
from ..commands.calendar_shortcuts import (
    _cmd_calendar_agenda,
    _cmd_calendar_create,
    _cmd_calendar_freebusy,
    _cmd_calendar_room_find,
    _cmd_calendar_suggestion,
    _cmd_calendar_update,
)
from ..commands.drive_shortcuts import (
    _cmd_drive_add_comment,
    _cmd_drive_apply_permission,
    _cmd_drive_create_folder,
    _cmd_drive_create_shortcut,
    _cmd_drive_delete,
    _cmd_drive_download,
    _cmd_drive_export_download,
    _cmd_drive_export_shortcut,
    _cmd_drive_import_shortcut,
    _cmd_drive_move_shortcut,
    _cmd_drive_search,
    _cmd_drive_task_result_shortcut,
    _cmd_drive_upload,
)
from ..commands.docs_shortcuts import (
    _cmd_docs_create,
    _cmd_docs_fetch,
    _cmd_docs_media_download,
    _cmd_docs_media_insert,
    _cmd_docs_media_preview,
    _cmd_docs_media_upload,
    _cmd_docs_search,
    _cmd_docs_update,
    _cmd_whiteboard_update as _cmd_docs_whiteboard_update,
)
from ..commands.event_shortcuts import _cmd_event_subscribe
from ..commands.im_shortcuts import (
    _cmd_im_chat_create,
    _cmd_im_chat_messages_list,
    _cmd_im_chat_search,
    _cmd_im_chat_update,
    _cmd_im_messages_mget,
    _cmd_im_messages_reply,
    _cmd_im_messages_resources_download,
    _cmd_im_messages_search,
    _cmd_im_messages_send,
    _cmd_im_threads_messages_list,
)
from ..commands.mail import _cmd_message_send_markdown
from ..commands.mail_shortcuts import (
    _cmd_mail_draft_create,
    _cmd_mail_draft_edit,
    _cmd_mail_p6_shortcut,
    _cmd_mail_thread,
)
from ..commands.minutes import _cmd_minutes_download
from ..commands.minutes_shortcuts import _cmd_minutes_search
from ..commands.okr_shortcuts import _cmd_okr_shortcut
from ..commands.org import _cmd_calendar_attach_material, _cmd_calendar_rsvp
from ..commands.sheets_shortcuts import _cmd_sheets_shortcut
from ..commands.slides_shortcuts import _cmd_slides_shortcut
from ..commands.task_shortcuts import (
    _cmd_task_assign_shortcut,
    _cmd_task_comment_shortcut,
    _cmd_task_complete_shortcut,
    _cmd_task_create_shortcut,
    _cmd_task_delete_shortcut,
    _cmd_task_followers_shortcut,
    _cmd_task_get_my_tasks_shortcut,
    _cmd_task_get_related_tasks_shortcut,
    _cmd_task_reminder_shortcut,
    _cmd_task_reopen_shortcut,
    _cmd_task_search_shortcut,
    _cmd_task_set_ancestor_shortcut,
    _cmd_task_subscribe_event_shortcut,
    _cmd_task_tasklist_create_shortcut,
    _cmd_task_tasklist_members_shortcut,
    _cmd_task_tasklist_search_shortcut,
    _cmd_task_tasklist_task_add_shortcut,
    _cmd_task_update_shortcut,
)
from ..commands.vc_shortcuts import (
    _cmd_vc_notes,
    _cmd_vc_recording,
    _cmd_vc_search,
)
from ..commands.wiki_shortcuts import (
    _cmd_wiki_delete_space,
    _cmd_wiki_move,
    _cmd_wiki_node_create,
)
from ..commands.whiteboard_shortcuts import (
    _cmd_whiteboard_query,
    _cmd_whiteboard_update,
)
from ..context import CLIContext, build_cli_context, with_runtime_options
from ..runtime.identity import identity_to_auth_mode, resolve_identity


ShortcutCallback = Callable[[CLIContext, dict[str, Any]], Any]


SHEETS_SHORTCUT_NAMES = (
    "info",
    "read",
    "write",
    "write-image",
    "append",
    "find",
    "create",
    "export",
    "merge-cells",
    "unmerge-cells",
    "replace",
    "set-style",
    "batch-set-style",
    "add-dimension",
    "insert-dimension",
    "update-dimension",
    "move-dimension",
    "delete-dimension",
    "create-filter-view",
    "update-filter-view",
    "list-filter-views",
    "get-filter-view",
    "delete-filter-view",
    "create-filter-view-condition",
    "update-filter-view-condition",
    "list-filter-view-conditions",
    "get-filter-view-condition",
    "delete-filter-view-condition",
    "set-dropdown",
    "update-dropdown",
    "get-dropdown",
    "delete-dropdown",
    "media-upload",
    "create-float-image",
    "update-float-image",
    "get-float-image",
    "list-float-images",
    "delete-float-image",
)


SLIDES_SHORTCUT_NAMES = ("create", "media-upload", "replace-slide")


MAIL_P6_SHORTCUTS = (
    ("message", "Fetch a mail message with full or plain-text body", "read", ("user", "bot")),
    ("messages", "Batch fetch mail messages by ID", "read", ("user", "bot")),
    ("triage", "List or search mailbox messages for triage", "read", ("user", "bot")),
    ("watch", "Subscribe to mailbox events and return watch metadata", "read", ("user",)),
    ("reply", "Create or send a reply draft for a message", "write", ("user",)),
    ("reply-all", "Create or send a reply-all draft for a message", "write", ("user",)),
    ("send", "Compose a new mail draft and optionally send it", "write", ("user",)),
    ("forward", "Create or send a forward draft for a message", "write", ("user",)),
    ("send-receipt", "Send a read receipt for an incoming message", "write", ("user",)),
    ("decline-receipt", "Dismiss a read-receipt request without sending a receipt", "write", ("user",)),
    ("signature", "List or inspect mail signatures", "read", ("user",)),
    ("share-to-chat", "Share a mail message or thread to an IM chat", "write", ("user",)),
    ("template-create", "Create a personal mail template", "write", ("user",)),
    ("template-update", "Update a personal mail template", "write", ("user",)),
)


OKR_SHORTCUTS = (
    ("cycle-list", "List OKR cycles for a user", "read"),
    ("cycle-detail", "List objectives and key results under an OKR cycle", "read"),
    ("progress-list", "List progress for an objective or key result", "read"),
    ("progress-get", "Get an OKR progress record by ID", "read"),
    ("progress-create", "Create an OKR progress record", "write"),
    ("progress-update", "Update an OKR progress record", "write"),
    ("progress-delete", "Delete an OKR progress record", "write"),
    ("upload-image", "Upload an image for OKR progress rich text", "write"),
)


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


def _mail_p6_specs() -> list[ShortcutSpec]:
    return [
        ShortcutSpec(
            service="mail",
            name=name,
            description=description,
            risk=risk,
            supported_identities=supported_identities,
            command_factory=lambda shortcut_name=name: _mail_p6_command(shortcut_name),
        )
        for name, description, risk, supported_identities in MAIL_P6_SHORTCUTS
    ]


def _okr_specs() -> list[ShortcutSpec]:
    return [
        ShortcutSpec(
            service="okr",
            name=name,
            description=description,
            risk=risk,
            supported_identities=("user", "bot"),
            command_factory=lambda shortcut_name=name: _okr_command(shortcut_name),
        )
        for name, description, risk in OKR_SHORTCUTS
    ]


def _base_specs() -> list[ShortcutSpec]:
    return [
        ShortcutSpec(
            service="base",
            name=name,
            description=f"Base {name.replace('-', ' ')}",
            risk="read" if any(token in name for token in ("list", "get", "search")) else "write",
            supported_identities=("user", "bot"),
            command_factory=lambda shortcut_name=name: _base_command(shortcut_name),
        )
        for name in BASE_SHORTCUT_NAMES
    ]


def list_shortcuts(service: str | None = None) -> list[ShortcutSpec]:
    items = [
        *_base_specs(),
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
            service="contact",
            name="get-user",
            description="Get user info (omit --user-id for self; provide --user-id for a specific user)",
            risk="read",
            supported_identities=("bot", "user"),
            command_factory=_contact_get_user_command,
        ),
        ShortcutSpec(
            service="contact",
            name="search-user",
            description="Search users by keyword, open_id list, or search filters",
            risk="read",
            supported_identities=("user",),
            command_factory=_contact_search_user_command,
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
            service="minutes",
            name="search",
            description="Search minutes by keyword, owners, participants, and time range",
            risk="read",
            supported_identities=("user",),
            command_factory=_minutes_search_command,
        ),
        ShortcutSpec(
            service="calendar",
            name="agenda",
            description="List calendar event instances for a time range",
            risk="read",
            supported_identities=("bot", "user"),
            command_factory=_calendar_agenda_command,
        ),
        ShortcutSpec(
            service="calendar",
            name="create",
            description="Create a calendar event and optionally invite attendees",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=_calendar_create_command,
        ),
        ShortcutSpec(
            service="calendar",
            name="freebusy",
            description="Query user free/busy information",
            risk="read",
            supported_identities=("bot", "user"),
            command_factory=_calendar_freebusy_command,
        ),
        ShortcutSpec(
            service="calendar",
            name="room-find",
            description="Search available meeting rooms for a time slot",
            risk="read",
            supported_identities=("bot", "user"),
            command_factory=_calendar_room_find_command,
        ),
        ShortcutSpec(
            service="calendar",
            name="suggestion",
            description="Find suggested meeting times for attendees",
            risk="read",
            supported_identities=("bot", "user"),
            command_factory=_calendar_suggestion_command,
        ),
        ShortcutSpec(
            service="calendar",
            name="update",
            description="Update a calendar event and incrementally add or remove attendees",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=_calendar_update_command,
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
            name="upload",
            description="Upload a local file to Drive",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=_drive_upload_command,
        ),
        ShortcutSpec(
            service="drive",
            name="download",
            description="Download a Drive file to the local filesystem",
            risk="read",
            supported_identities=("bot", "user"),
            command_factory=_drive_download_command,
        ),
        ShortcutSpec(
            service="drive",
            name="delete",
            description="Delete a Drive file, folder, shortcut, or document",
            risk="high-risk-write",
            supported_identities=("bot", "user"),
            command_factory=_drive_delete_command,
        ),
        ShortcutSpec(
            service="drive",
            name="create-folder",
            description="Create a folder in Drive",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=_drive_create_folder_command,
        ),
        ShortcutSpec(
            service="drive",
            name="create-shortcut",
            description="Create a Drive shortcut in another folder",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=_drive_create_shortcut_command,
        ),
        ShortcutSpec(
            service="drive",
            name="add-comment",
            description="Add a comment to a Drive document",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=_drive_add_comment_command,
        ),
        ShortcutSpec(
            service="drive",
            name="apply-permission",
            description="Apply to the document owner for view or edit permission",
            risk="write",
            supported_identities=("user",),
            command_factory=_drive_apply_permission_command,
        ),
        ShortcutSpec(
            service="drive",
            name="export-download",
            description="Download an exported file by file_token",
            risk="read",
            supported_identities=("bot", "user"),
            command_factory=_drive_export_download_command,
        ),
        ShortcutSpec(
            service="drive",
            name="search",
            description="Search Lark docs, Wiki, and spreadsheet files with flat filters",
            risk="read",
            supported_identities=("user",),
            command_factory=_drive_search_command,
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
            service="docs",
            name="search",
            description="Search Lark docs, Wiki, and spreadsheet files",
            risk="read",
            supported_identities=("user",),
            command_factory=_docs_search_command,
        ),
        ShortcutSpec(
            service="docs",
            name="create",
            description="Create a document through docs_ai OpenAPI",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=_docs_create_command,
        ),
        ShortcutSpec(
            service="docs",
            name="fetch",
            description="Fetch document content through docs_ai OpenAPI",
            risk="read",
            supported_identities=("bot", "user"),
            command_factory=_docs_fetch_command,
        ),
        ShortcutSpec(
            service="docs",
            name="update",
            description="Update a document through docs_ai OpenAPI",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=_docs_update_command,
        ),
        ShortcutSpec(
            service="docs",
            name="media-insert",
            description="Insert a local image or file into a Lark document",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=_docs_media_insert_command,
        ),
        ShortcutSpec(
            service="docs",
            name="media-upload",
            description="Upload media file to a document block",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=_docs_media_upload_command,
        ),
        ShortcutSpec(
            service="docs",
            name="media-preview",
            description="Preview document media file",
            risk="read",
            supported_identities=("bot", "user"),
            command_factory=_docs_media_preview_command,
        ),
        ShortcutSpec(
            service="docs",
            name="media-download",
            description="Download document media or whiteboard thumbnail",
            risk="read",
            supported_identities=("bot", "user"),
            command_factory=_docs_media_download_command,
        ),
        ShortcutSpec(
            service="docs",
            name="whiteboard-update",
            description="Update an existing whiteboard from the docs command namespace",
            risk="high-risk-write",
            supported_identities=("bot", "user"),
            command_factory=_docs_whiteboard_update_command,
        ),
        ShortcutSpec(
            service="event",
            name="subscribe",
            description="Subscribe to Lark events or consume a single stdin event payload",
            risk="read",
            supported_identities=("bot",),
            command_factory=_event_subscribe_command,
        ),
        ShortcutSpec(
            service="im",
            name="chat-create",
            description="Create a group chat and optionally return its share link",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=_im_chat_create_command,
        ),
        ShortcutSpec(
            service="im",
            name="chat-messages-list",
            description="List messages in a chat container",
            risk="read",
            supported_identities=("bot", "user"),
            command_factory=_im_chat_messages_list_command,
        ),
        ShortcutSpec(
            service="im",
            name="chat-search",
            description="Search chats by query, type, and member filters",
            risk="read",
            supported_identities=("bot", "user"),
            command_factory=_im_chat_search_command,
        ),
        ShortcutSpec(
            service="im",
            name="chat-update",
            description="Update chat metadata",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=_im_chat_update_command,
        ),
        ShortcutSpec(
            service="im",
            name="messages-mget",
            description="Batch fetch messages by message ID",
            risk="read",
            supported_identities=("bot", "user"),
            command_factory=_im_messages_mget_command,
        ),
        ShortcutSpec(
            service="im",
            name="messages-reply",
            description="Reply to a message, optionally in thread",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=_im_messages_reply_command,
        ),
        ShortcutSpec(
            service="im",
            name="messages-resources-download",
            description="Download a message resource to the local filesystem",
            risk="read",
            supported_identities=("bot", "user"),
            command_factory=_im_messages_resources_download_command,
        ),
        ShortcutSpec(
            service="im",
            name="messages-search",
            description="Search messages and optionally hydrate matched message/chat details",
            risk="read",
            supported_identities=("bot", "user"),
            command_factory=_im_messages_search_command,
        ),
        ShortcutSpec(
            service="im",
            name="messages-send",
            description="Send a message to a chat or direct user",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=_im_messages_send_command,
        ),
        ShortcutSpec(
            service="im",
            name="threads-messages-list",
            description="List messages in a thread container",
            risk="read",
            supported_identities=("bot", "user"),
            command_factory=_im_threads_messages_list_command,
        ),
        *[
            ShortcutSpec(
                service="sheets",
                name=name,
                description=f"Lark Sheets shortcut +{name}",
                risk="read" if name in {"info", "read", "find", "list-filter-views", "get-filter-view", "list-filter-view-conditions", "get-filter-view-condition", "get-dropdown", "get-float-image", "list-float-images"} else "write",
                supported_identities=("bot", "user"),
                command_factory=lambda shortcut_name=name: _sheets_shortcut_command(shortcut_name),
            )
            for name in SHEETS_SHORTCUT_NAMES
        ],
        *[
            ShortcutSpec(
                service="slides",
                name=name,
                description=f"Lark Slides shortcut +{name}",
                risk="write",
                supported_identities=("bot", "user"),
                command_factory=lambda shortcut_name=name: _slides_shortcut_command(shortcut_name),
            )
            for name in SLIDES_SHORTCUT_NAMES
        ],
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
            service="task",
            name="update",
            description="Update task attributes",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=lambda: _task_p5_command("update", _cmd_task_update_shortcut),
        ),
        ShortcutSpec(
            service="task",
            name="set-ancestor",
            description="Set a task ancestor",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=lambda: _task_p5_command("set-ancestor", _cmd_task_set_ancestor_shortcut),
        ),
        ShortcutSpec(
            service="task",
            name="get-related-tasks",
            description="Get related tasks",
            risk="read",
            supported_identities=("bot", "user"),
            command_factory=lambda: _task_p5_command("get-related-tasks", _cmd_task_get_related_tasks_shortcut),
        ),
        ShortcutSpec(
            service="task",
            name="search",
            description="Search tasks",
            risk="read",
            supported_identities=("user",),
            command_factory=lambda: _task_p5_command("search", _cmd_task_search_shortcut),
        ),
        ShortcutSpec(
            service="task",
            name="subscribe-event",
            description="Subscribe to task events",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=lambda: _task_p5_command("subscribe-event", _cmd_task_subscribe_event_shortcut),
        ),
        ShortcutSpec(
            service="task",
            name="tasklist-create",
            description="Create a tasklist and optionally seed tasks",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=lambda: _task_p5_command("tasklist-create", _cmd_task_tasklist_create_shortcut),
        ),
        ShortcutSpec(
            service="task",
            name="tasklist-search",
            description="Search tasklists",
            risk="read",
            supported_identities=("user",),
            command_factory=lambda: _task_p5_command("tasklist-search", _cmd_task_tasklist_search_shortcut),
        ),
        ShortcutSpec(
            service="task",
            name="tasklist-task-add",
            description="Add tasks to a tasklist",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=lambda: _task_p5_command("tasklist-task-add", _cmd_task_tasklist_task_add_shortcut),
        ),
        ShortcutSpec(
            service="task",
            name="tasklist-members",
            description="Add or remove tasklist members",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=lambda: _task_p5_command("tasklist-members", _cmd_task_tasklist_members_shortcut),
        ),
        ShortcutSpec(
            service="mail",
            name="send-markdown",
            description="Render markdown and send it as an email message",
            risk="write",
            supported_identities=("user", "bot"),
            command_factory=_mail_send_markdown_command,
        ),
        *_mail_p6_specs(),
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
        *_okr_specs(),
        ShortcutSpec(
            service="vc",
            name="search",
            description="Search meeting records by keyword and filters",
            risk="read",
            supported_identities=("user",),
            command_factory=_vc_search_command,
        ),
        ShortcutSpec(
            service="vc",
            name="notes",
            description="Query meeting notes via meeting IDs, minute tokens, or calendar event IDs",
            risk="read",
            supported_identities=("user",),
            command_factory=_vc_notes_command,
        ),
        ShortcutSpec(
            service="vc",
            name="recording",
            description="Query meeting recording info and extract minute tokens",
            risk="read",
            supported_identities=("user",),
            command_factory=_vc_recording_command,
        ),
        ShortcutSpec(
            service="wiki",
            name="move",
            description="Move a wiki node, or move a Drive document into Wiki",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=_wiki_move_command,
        ),
        ShortcutSpec(
            service="wiki",
            name="node-create",
            description="Create a wiki node with automatic space resolution",
            risk="write",
            supported_identities=("bot", "user"),
            command_factory=_wiki_node_create_command,
        ),
        ShortcutSpec(
            service="wiki",
            name="delete-space",
            description="Delete a wiki space, polling the async delete task when needed",
            risk="high-risk-write",
            supported_identities=("bot", "user"),
            command_factory=_wiki_delete_space_command,
        ),
        ShortcutSpec(
            service="whiteboard",
            name="query",
            description="Query a whiteboard as image, code, or raw nodes",
            risk="read",
            supported_identities=("bot", "user"),
            command_factory=_whiteboard_query_command,
        ),
        ShortcutSpec(
            service="whiteboard",
            name="update",
            description="Update an existing whiteboard from raw, PlantUML, or Mermaid input",
            risk="high-risk-write",
            supported_identities=("bot", "user"),
            command_factory=_whiteboard_update_command,
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


def _contact_get_user_command() -> click.Command:
    spec = get_shortcut("contact.+get-user")
    assert spec is not None

    @click.command(name="+get-user", help=spec.description)
    @click.option("--user-id")
    @click.option("--user-id-type", default="open_id", show_default=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        steps = [
            {"action": "authen.user_info", "when": "--user-id omitted"},
            {"action": "contact.users.get", "identity": "bot", "when": "--user-id provided"},
            {"action": "contact.users.basic_batch", "identity": "user", "when": "--user-id provided"},
        ]
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_contact_get_user,
            params=params,
            dry_run=dry_run,
            group="contact",
            command_field="contact_command",
            command_name="get-user",
            steps=steps,
        )

    return _command


def _contact_search_user_command() -> click.Command:
    spec = get_shortcut("contact.+search-user")
    assert spec is not None

    @click.command(name="+search-user", help=spec.description)
    @click.option("--query")
    @click.option("--queries")
    @click.option("--user-ids")
    @click.option("--has-chatted", is_flag=True)
    @click.option("--has-enterprise-email", is_flag=True)
    @click.option("--exclude-external-users", is_flag=True)
    @click.option("--left-organization", is_flag=True)
    @click.option("--lang")
    @click.option("--page-size", type=int, default=20, show_default=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_contact_search_user,
            params=params,
            dry_run=dry_run,
            group="contact",
            command_field="contact_command",
            command_name="search-user",
            steps=[{"action": "contact.users.search"}],
        )

    return _command


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


def _minutes_search_command() -> click.Command:
    spec = get_shortcut("minutes.+search")
    assert spec is not None

    @click.command(name="+search", help=spec.description)
    @click.option("--query")
    @click.option("--owner-ids")
    @click.option("--participant-ids")
    @click.option("--start")
    @click.option("--end")
    @click.option("--page-token")
    @click.option("--page-size", type=int, default=15, show_default=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_minutes_search,
            params=params,
            dry_run=dry_run,
            group="minutes",
            command_field="minutes_command",
            command_name="search",
            steps=[{"action": "minutes.search"}],
        )

    return _command


def _calendar_agenda_command() -> click.Command:
    spec = get_shortcut("calendar.+agenda")
    assert spec is not None

    @click.command(name="+agenda", help=spec.description)
    @click.option("--calendar-id", default="primary", show_default=True)
    @click.option("--start", required=True)
    @click.option("--end", required=True)
    @click.option("--page-size", type=int)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_calendar_agenda,
            params=params,
            dry_run=dry_run,
            group="calendar",
            command_field="calendar_command",
            command_name="agenda",
            steps=[{"action": "calendar.events.instance_view"}],
        )

    return _command


def _calendar_create_command() -> click.Command:
    spec = get_shortcut("calendar.+create")
    assert spec is not None

    @click.command(name="+create", help=spec.description)
    @click.option("--summary")
    @click.option("--start", required=True)
    @click.option("--end", required=True)
    @click.option("--description")
    @click.option("--attendee-ids")
    @click.option("--calendar-id", default="primary", show_default=True)
    @click.option("--rrule")
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_calendar_create,
            params=params,
            dry_run=dry_run,
            group="calendar",
            command_field="calendar_command",
            command_name="create",
            steps=[
                {"action": "calendar.events.create"},
                {"action": "calendar.event_attendees.create", "optional": True},
            ],
        )

    return _command


def _calendar_freebusy_command() -> click.Command:
    spec = get_shortcut("calendar.+freebusy")
    assert spec is not None

    @click.command(name="+freebusy", help=spec.description)
    @click.option("--user-id")
    @click.option("--user-ids")
    @click.option("--start", required=True)
    @click.option("--end", required=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_calendar_freebusy,
            params=params,
            dry_run=dry_run,
            group="calendar",
            command_field="calendar_command",
            command_name="freebusy",
            steps=[{"action": "calendar.freebusy.list"}],
        )

    return _command


def _calendar_room_find_command() -> click.Command:
    spec = get_shortcut("calendar.+room-find")
    assert spec is not None

    @click.command(name="+room-find", help=spec.description)
    @click.option("--slot", required=True)
    @click.option("--min-capacity", type=int)
    @click.option("--building-id")
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_calendar_room_find,
            params=params,
            dry_run=dry_run,
            group="calendar",
            command_field="calendar_command",
            command_name="room-find",
            steps=[{"action": "calendar.meeting_room.search"}],
        )

    return _command


def _calendar_suggestion_command() -> click.Command:
    spec = get_shortcut("calendar.+suggestion")
    assert spec is not None

    @click.command(name="+suggestion", help=spec.description)
    @click.option("--attendee-ids")
    @click.option("--duration-minutes", type=int, default=30, show_default=True)
    @click.option("--start")
    @click.option("--end")
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_calendar_suggestion,
            params=params,
            dry_run=dry_run,
            group="calendar",
            command_field="calendar_command",
            command_name="suggestion",
            steps=[{"action": "calendar.freebusy.suggestion"}],
        )

    return _command


def _calendar_update_command() -> click.Command:
    spec = get_shortcut("calendar.+update")
    assert spec is not None

    @click.command(name="+update", help=spec.description)
    @click.option("--calendar-id", default="primary", show_default=True)
    @click.option("--event-id", required=True)
    @click.option("--summary")
    @click.option("--description")
    @click.option("--start")
    @click.option("--end")
    @click.option("--rrule")
    @click.option("--add-attendee-ids")
    @click.option("--remove-attendee-ids")
    @click.option("--notify/--no-notify", default=True, show_default=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_calendar_update,
            params=params,
            dry_run=dry_run,
            group="calendar",
            command_field="calendar_command",
            command_name="update",
            steps=[
                {"action": "calendar.events.patch", "optional": True},
                {"action": "calendar.event_attendees.batch_delete", "optional": True},
                {"action": "calendar.event_attendees.create", "optional": True},
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


def _drive_upload_command() -> click.Command:
    spec = get_shortcut("drive.+upload")
    assert spec is not None

    @click.command(name="+upload", help=spec.description)
    @click.option("--file", "file", required=True)
    @click.option("--folder-token")
    @click.option("--wiki-token")
    @click.option("--name")
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_drive_upload,
            params=params,
            dry_run=dry_run,
            group="drive",
            command_field="drive_command",
            command_name="upload",
            steps=[{"action": "drive.files.upload_all"}],
        )

    return _command


def _drive_download_command() -> click.Command:
    spec = get_shortcut("drive.+download")
    assert spec is not None

    @click.command(name="+download", help=spec.description)
    @click.option("--file-token", required=True)
    @click.option("--output")
    @click.option("--overwrite", is_flag=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_drive_download,
            params=params,
            dry_run=dry_run,
            group="drive",
            command_field="drive_command",
            command_name="download",
            steps=[{"action": "drive.files.download"}],
        )

    return _command


def _drive_delete_command() -> click.Command:
    spec = get_shortcut("drive.+delete")
    assert spec is not None

    @click.command(name="+delete", help=spec.description)
    @click.option("--file-token", required=True)
    @click.option("--type", required=True)
    @click.option("--yes", is_flag=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_drive_delete,
            params=params,
            dry_run=dry_run,
            group="drive",
            command_field="drive_command",
            command_name="delete",
            steps=[{"action": "drive.files.delete"}],
        )

    return _command


def _drive_create_folder_command() -> click.Command:
    spec = get_shortcut("drive.+create-folder")
    assert spec is not None

    @click.command(name="+create-folder", help=spec.description)
    @click.option("--name", required=True)
    @click.option("--folder-token")
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_drive_create_folder,
            params=params,
            dry_run=dry_run,
            group="drive",
            command_field="drive_command",
            command_name="create-folder",
            steps=[{"action": "drive.files.create_folder"}],
        )

    return _command


def _drive_create_shortcut_command() -> click.Command:
    spec = get_shortcut("drive.+create-shortcut")
    assert spec is not None

    @click.command(name="+create-shortcut", help=spec.description)
    @click.option("--file-token", required=True)
    @click.option("--type", required=True)
    @click.option("--folder-token", required=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_drive_create_shortcut,
            params=params,
            dry_run=dry_run,
            group="drive",
            command_field="drive_command",
            command_name="create-shortcut",
            steps=[{"action": "drive.files.create_shortcut"}],
        )

    return _command


def _drive_add_comment_command() -> click.Command:
    spec = get_shortcut("drive.+add-comment")
    assert spec is not None

    @click.command(name="+add-comment", help=spec.description)
    @click.option("--doc", required=True)
    @click.option("--type")
    @click.option("--content", required=True)
    @click.option("--full-comment", is_flag=True)
    @click.option("--selection-with-ellipsis")
    @click.option("--block-id")
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_drive_add_comment,
            params=params,
            dry_run=dry_run,
            group="drive",
            command_field="drive_command",
            command_name="add-comment",
            steps=[{"action": "drive.comments.create"}],
        )

    return _command


def _drive_apply_permission_command() -> click.Command:
    spec = get_shortcut("drive.+apply-permission")
    assert spec is not None

    @click.command(name="+apply-permission", help=spec.description)
    @click.option("--token", required=True)
    @click.option("--type", required=True)
    @click.option("--perm", type=click.Choice(["view", "edit"]), required=True)
    @click.option("--remark")
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_drive_apply_permission,
            params=params,
            dry_run=dry_run,
            group="drive",
            command_field="drive_command",
            command_name="apply-permission",
            steps=[{"action": "drive.permissions.apply"}],
        )

    return _command


def _drive_export_download_command() -> click.Command:
    spec = get_shortcut("drive.+export-download")
    assert spec is not None

    @click.command(name="+export-download", help=spec.description)
    @click.option("--file-token", required=True)
    @click.option("--file-name")
    @click.option("--output-dir", default=".", show_default=True)
    @click.option("--overwrite", is_flag=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_drive_export_download,
            params=params,
            dry_run=dry_run,
            group="drive",
            command_field="drive_command",
            command_name="export-download",
            steps=[{"action": "drive.export_tasks.file.download"}],
        )

    return _command


def _drive_search_command() -> click.Command:
    spec = get_shortcut("drive.+search")
    assert spec is not None

    @click.command(name="+search", help=spec.description)
    @click.option("--query")
    @click.option("--doc-types")
    @click.option("--folder-tokens")
    @click.option("--space-ids")
    @click.option("--page-token")
    @click.option("--page-size", type=int, default=15, show_default=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_drive_search,
            params=params,
            dry_run=dry_run,
            group="drive",
            command_field="drive_command",
            command_name="search",
            steps=[{"action": "search.doc_wiki.search"}],
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


def _docs_search_command() -> click.Command:
    spec = get_shortcut("docs.+search")
    assert spec is not None

    @click.command(name="+search", help=spec.description)
    @click.option("--query")
    @click.option("--filter")
    @click.option("--page-token")
    @click.option("--page-size", type=int, default=15, show_default=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_docs_search,
            params=params,
            dry_run=dry_run,
            group="docs",
            command_field="docs_command",
            command_name="search",
            steps=[{"action": "search.doc_wiki.search"}],
        )

    return _command


def _docs_create_command() -> click.Command:
    spec = get_shortcut("docs.+create")
    assert spec is not None

    @click.command(name="+create", help=spec.description)
    @click.option("--content", required=True)
    @click.option("--doc-format", default="xml", show_default=True)
    @click.option("--parent-token")
    @click.option("--parent-position")
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_docs_create,
            params=params,
            dry_run=dry_run,
            group="docs",
            command_field="docs_command",
            command_name="create",
            steps=[{"action": "docs_ai.documents.create"}],
        )

    return _command


def _docs_fetch_command() -> click.Command:
    spec = get_shortcut("docs.+fetch")
    assert spec is not None

    @click.command(name="+fetch", help=spec.description)
    @click.option("--doc", required=True)
    @click.option("--doc-format", default="xml", show_default=True)
    @click.option(
        "--detail",
        type=click.Choice(["simple", "with-ids", "full"]),
        default="simple",
        show_default=True,
    )
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_docs_fetch,
            params=params,
            dry_run=dry_run,
            group="docs",
            command_field="docs_command",
            command_name="fetch",
            steps=[{"action": "docs_ai.documents.fetch"}],
        )

    return _command


def _docs_update_command() -> click.Command:
    spec = get_shortcut("docs.+update")
    assert spec is not None

    @click.command(name="+update", help=spec.description)
    @click.option("--doc", required=True)
    @click.option("--command", required=True)
    @click.option("--content")
    @click.option("--doc-format", default="xml", show_default=True)
    @click.option("--block-id")
    @click.option("--pattern")
    @click.option("--src-block-ids")
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_docs_update,
            params=params,
            dry_run=dry_run,
            group="docs",
            command_field="docs_command",
            command_name="update",
            steps=[{"action": "docs_ai.documents.update"}],
        )

    return _command


def _docs_media_insert_command() -> click.Command:
    spec = get_shortcut("docs.+media-insert")
    assert spec is not None

    @click.command(name="+media-insert", help=spec.description)
    @click.option("--file", "file", required=True)
    @click.option("--doc", required=True)
    @click.option("--type", default="image", show_default=True)
    @click.option("--caption")
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_docs_media_insert,
            params=params,
            dry_run=dry_run,
            group="docs",
            command_field="docs_command",
            command_name="media-insert",
            steps=[
                {"action": "docx.blocks.get"},
                {"action": "docx.blocks.children.create"},
                {"action": "drive.medias.upload_all"},
                {"action": "docx.blocks.batch_update"},
            ],
        )

    return _command


def _docs_media_upload_command() -> click.Command:
    spec = get_shortcut("docs.+media-upload")
    assert spec is not None

    @click.command(name="+media-upload", help=spec.description)
    @click.option("--file", "file", required=True)
    @click.option("--parent-type", required=True)
    @click.option("--parent-node", required=True)
    @click.option("--doc-id")
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_docs_media_upload,
            params=params,
            dry_run=dry_run,
            group="docs",
            command_field="docs_command",
            command_name="media-upload",
            steps=[{"action": "drive.medias.upload_all"}],
        )

    return _command


def _docs_media_preview_command() -> click.Command:
    spec = get_shortcut("docs.+media-preview")
    assert spec is not None

    @click.command(name="+media-preview", help=spec.description)
    @click.option("--token", required=True)
    @click.option("--output", required=True)
    @click.option("--overwrite", is_flag=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_docs_media_preview,
            params=params,
            dry_run=dry_run,
            group="docs",
            command_field="docs_command",
            command_name="media-preview",
            steps=[{"action": "drive.medias.preview_download"}],
        )

    return _command


def _docs_media_download_command() -> click.Command:
    spec = get_shortcut("docs.+media-download")
    assert spec is not None

    @click.command(name="+media-download", help=spec.description)
    @click.option("--token", required=True)
    @click.option("--type", default="media", show_default=True)
    @click.option("--output", required=True)
    @click.option("--overwrite", is_flag=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_docs_media_download,
            params=params,
            dry_run=dry_run,
            group="docs",
            command_field="docs_command",
            command_name="media-download",
            steps=[{"action": "drive.medias.download"}],
        )

    return _command


def _docs_whiteboard_update_command() -> click.Command:
    spec = get_shortcut("docs.+whiteboard-update")
    assert spec is not None

    @click.command(name="+whiteboard-update", help=spec.description)
    @click.option("--whiteboard-token", required=True)
    @click.option("--source", required=True)
    @click.option(
        "--input-format",
        type=click.Choice(["raw", "plantuml", "mermaid"]),
        default="raw",
        show_default=True,
    )
    @click.option("--overwrite", is_flag=True)
    @click.option("--idempotent-token")
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_docs_whiteboard_update,
            params=params,
            dry_run=dry_run,
            group="docs",
            command_field="docs_command",
            command_name="whiteboard-update",
            steps=[{"action": "board.whiteboards.nodes.update"}],
        )

    return _command


def _whiteboard_query_command() -> click.Command:
    spec = get_shortcut("whiteboard.+query")
    assert spec is not None

    @click.command(name="+query", help=spec.description)
    @click.option("--whiteboard-token", required=True)
    @click.option(
        "--output-as",
        type=click.Choice(["raw", "code", "image"]),
        default="raw",
        show_default=True,
    )
    @click.option("--output")
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_whiteboard_query,
            params=params,
            dry_run=dry_run,
            group="whiteboard",
            command_field="whiteboard_command",
            command_name="query",
            steps=[{"action": "board.whiteboards.nodes.query"}],
        )

    return _command


def _whiteboard_update_command() -> click.Command:
    spec = get_shortcut("whiteboard.+update")
    assert spec is not None

    @click.command(name="+update", help=spec.description)
    @click.option("--whiteboard-token", required=True)
    @click.option("--source", required=True)
    @click.option(
        "--input-format",
        type=click.Choice(["raw", "plantuml", "mermaid"]),
        default="raw",
        show_default=True,
    )
    @click.option("--overwrite", is_flag=True)
    @click.option("--idempotent-token")
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_whiteboard_update,
            params=params,
            dry_run=dry_run,
            group="whiteboard",
            command_field="whiteboard_command",
            command_name="update",
            steps=[{"action": "board.whiteboards.nodes.update"}],
        )

    return _command


def _event_subscribe_command() -> click.Command:
    spec = get_shortcut("event.+subscribe")
    assert spec is not None

    @click.command(name="+subscribe", help=spec.description)
    @click.option("--output-dir")
    @click.option("--route", multiple=True)
    @click.option("--compact", is_flag=True)
    @click.option("--json", "json_output", is_flag=True)
    @click.option("--event-types")
    @click.option("--filter")
    @click.option("--quiet", is_flag=True)
    @click.option("--force", is_flag=True)
    @click.option("--stdin", is_flag=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_event_subscribe,
            params=params,
            dry_run=dry_run,
            group="event",
            command_field="event_command",
            command_name="subscribe",
            steps=[{"action": "event.subscribe"}],
        )

    return _command


def _im_chat_create_command() -> click.Command:
    spec = get_shortcut("im.+chat-create")
    assert spec is not None

    @click.command(name="+chat-create", help=spec.description)
    @click.option("--name")
    @click.option("--description")
    @click.option("--users")
    @click.option("--bots")
    @click.option("--owner")
    @click.option("--type", default="private", show_default=True)
    @click.option("--set-bot-manager", is_flag=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_im_chat_create,
            params=params,
            dry_run=dry_run,
            group="im",
            command_field="im_command",
            command_name="chat-create",
            steps=[
                {"action": "im.chats.create"},
                {"action": "im.chats.link", "optional": True},
            ],
        )

    return _command


def _im_chat_update_command() -> click.Command:
    spec = get_shortcut("im.+chat-update")
    assert spec is not None

    @click.command(name="+chat-update", help=spec.description)
    @click.option("--chat-id", required=True)
    @click.option("--name")
    @click.option("--description")
    @click.option("--owner")
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_im_chat_update,
            params=params,
            dry_run=dry_run,
            group="im",
            command_field="im_command",
            command_name="chat-update",
            steps=[{"action": "im.chats.update"}],
        )

    return _command


def _im_chat_messages_list_command() -> click.Command:
    spec = get_shortcut("im.+chat-messages-list")
    assert spec is not None

    @click.command(name="+chat-messages-list", help=spec.description)
    @click.option("--chat-id", required=True)
    @click.option("--sort", type=click.Choice(["asc", "desc"]))
    @click.option("--page-size", type=int)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_im_chat_messages_list,
            params=params,
            dry_run=dry_run,
            group="im",
            command_field="im_command",
            command_name="chat-messages-list",
            steps=[{"action": "im.messages.list"}],
        )

    return _command


def _im_threads_messages_list_command() -> click.Command:
    spec = get_shortcut("im.+threads-messages-list")
    assert spec is not None

    @click.command(name="+threads-messages-list", help=spec.description)
    @click.option("--thread", "thread", required=True)
    @click.option("--sort", type=click.Choice(["asc", "desc"]))
    @click.option("--page-size", type=int)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_im_threads_messages_list,
            params=params,
            dry_run=dry_run,
            group="im",
            command_field="im_command",
            command_name="threads-messages-list",
            steps=[{"action": "im.messages.list", "container": "thread"}],
        )

    return _command


def _im_messages_send_command() -> click.Command:
    spec = get_shortcut("im.+messages-send")
    assert spec is not None

    @click.command(name="+messages-send", help=spec.description)
    @click.option("--chat-id")
    @click.option("--user-id")
    @click.option("--msg-type", default="text", show_default=True)
    @click.option("--content")
    @click.option("--text")
    @click.option("--idempotency-key")
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_im_messages_send,
            params=params,
            dry_run=dry_run,
            group="im",
            command_field="im_command",
            command_name="messages-send",
            steps=[{"action": "im.messages.create"}],
        )

    return _command


def _im_messages_reply_command() -> click.Command:
    spec = get_shortcut("im.+messages-reply")
    assert spec is not None

    @click.command(name="+messages-reply", help=spec.description)
    @click.option("--message-id", required=True)
    @click.option("--msg-type", default="text", show_default=True)
    @click.option("--content")
    @click.option("--text")
    @click.option("--reply-in-thread", is_flag=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_im_messages_reply,
            params=params,
            dry_run=dry_run,
            group="im",
            command_field="im_command",
            command_name="messages-reply",
            steps=[{"action": "im.messages.reply"}],
        )

    return _command


def _im_messages_mget_command() -> click.Command:
    spec = get_shortcut("im.+messages-mget")
    assert spec is not None

    @click.command(name="+messages-mget", help=spec.description)
    @click.option("--message-ids", required=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_im_messages_mget,
            params=params,
            dry_run=dry_run,
            group="im",
            command_field="im_command",
            command_name="messages-mget",
            steps=[{"action": "im.messages.mget"}],
        )

    return _command


def _im_chat_search_command() -> click.Command:
    spec = get_shortcut("im.+chat-search")
    assert spec is not None

    @click.command(name="+chat-search", help=spec.description)
    @click.option("--query")
    @click.option("--member-ids")
    @click.option("--search-types")
    @click.option("--sort-by")
    @click.option("--page-size", type=int)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_im_chat_search,
            params=params,
            dry_run=dry_run,
            group="im",
            command_field="im_command",
            command_name="chat-search",
            steps=[{"action": "im.chats.search"}],
        )

    return _command


def _im_messages_search_command() -> click.Command:
    spec = get_shortcut("im.+messages-search")
    assert spec is not None

    @click.command(name="+messages-search", help=spec.description)
    @click.option("--query")
    @click.option("--chat-id")
    @click.option("--chat-ids")
    @click.option("--sender")
    @click.option("--sender-ids")
    @click.option("--is-at-me", is_flag=True)
    @click.option("--at-chatter-ids")
    @click.option("--page-size", type=int)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_im_messages_search,
            params=params,
            dry_run=dry_run,
            group="im",
            command_field="im_command",
            command_name="messages-search",
            steps=[
                {"action": "im.messages.search"},
                {"action": "im.messages.mget", "optional": True},
                {"action": "im.chats.batch_query", "optional": True},
            ],
        )

    return _command


def _im_messages_resources_download_command() -> click.Command:
    spec = get_shortcut("im.+messages-resources-download")
    assert spec is not None

    @click.command(name="+messages-resources-download", help=spec.description)
    @click.option("--message-id", required=True)
    @click.option("--file-key", required=True)
    @click.option("--type", default="file", show_default=True)
    @click.option("--output", default=".", show_default=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_im_messages_resources_download,
            params=params,
            dry_run=dry_run,
            group="im",
            command_field="im_command",
            command_name="messages-resources-download",
            steps=[{"action": "im.message_resources.download"}],
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


def _sheets_shortcut_command(shortcut_name: str) -> click.Command:
    spec = get_shortcut(f"sheets.+{shortcut_name}")
    assert spec is not None

    @click.command(name=f"+{shortcut_name}", help=spec.description)
    @click.option("--url")
    @click.option("--spreadsheet-token")
    @click.option("--sheet-id")
    @click.option("--range")
    @click.option("--value-render-option")
    @click.option("--title")
    @click.option("--folder-token")
    @click.option("--headers")
    @click.option("--data")
    @click.option("--values")
    @click.option("--file", "file")
    @click.option("--parent-node")
    @click.option("--file-token")
    @click.option("--float-image-token")
    @click.option("--file-extension")
    @click.option("--find")
    @click.option("--replacement")
    @click.option("--condition")
    @click.option("--style")
    @click.option("--styles")
    @click.option("--merge-type")
    @click.option("--dimension")
    @click.option("--start-index", type=int)
    @click.option("--end-index", type=int)
    @click.option("--length", type=int)
    @click.option("--source-index", type=int)
    @click.option("--destination-index", type=int)
    @click.option("--inherit-style")
    @click.option("--fixed-size", type=int)
    @click.option("--visible", type=bool)
    @click.option("--filter-view-id")
    @click.option("--filter-view-name")
    @click.option("--name")
    @click.option("--condition-id")
    @click.option("--field-index", type=int)
    @click.option("--filter-type")
    @click.option("--compare-type")
    @click.option("--expected")
    @click.option("--options")
    @click.option("--condition-values")
    @click.option("--ranges")
    @click.option("--multiple", type=bool)
    @click.option("--highlight", type=bool)
    @click.option("--colors")
    @click.option("--data-validation-id")
    @click.option("--float-image-id")
    @click.option("--image-id")
    @click.option("--width", type=int)
    @click.option("--height", type=int)
    @click.option("--offset-x", type=int)
    @click.option("--offset-y", type=int)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_sheets_shortcut,
            params=params,
            dry_run=dry_run,
            group="sheets",
            command_field="sheets_command",
            command_name=shortcut_name,
            steps=[{"action": f"sheets.{shortcut_name.replace('-', '_')}"}],
        )

    return _command


def _slides_shortcut_command(shortcut_name: str) -> click.Command:
    spec = get_shortcut(f"slides.+{shortcut_name}")
    assert spec is not None

    @click.command(name=f"+{shortcut_name}", help=spec.description)
    @click.option("--title")
    @click.option("--slides")
    @click.option("--presentation")
    @click.option("--file", "file")
    @click.option("--slide-id")
    @click.option("--parts")
    @click.option("--revision-id", type=int, default=-1, show_default=True)
    @click.option("--tid")
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_slides_shortcut,
            params=params,
            dry_run=dry_run,
            group="slides",
            command_field="slides_command",
            command_name=shortcut_name,
            steps=[{"action": f"slides.{shortcut_name.replace('-', '_')}"}],
        )

    return _command


def _task_p5_command(shortcut_name: str, handler: Callable[[Any], Any]) -> click.Command:
    spec = get_shortcut(f"task.+{shortcut_name}")
    assert spec is not None

    @click.command(name=f"+{shortcut_name}", help=spec.description)
    @click.option("--task-id")
    @click.option("--summary")
    @click.option("--description")
    @click.option("--due")
    @click.option("--data")
    @click.option("--ancestor-id")
    @click.option("--query")
    @click.option("--page-token")
    @click.option("--page-size", type=int, default=50, show_default=True)
    @click.option("--creator")
    @click.option("--assignee")
    @click.option("--completed", is_flag=True)
    @click.option("--follower")
    @click.option("--resource-type")
    @click.option("--resource-id")
    @click.option("--event-type")
    @click.option("--name")
    @click.option("--member")
    @click.option("--tasklist-id")
    @click.option("--section-guid")
    @click.option("--add")
    @click.option("--remove")
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=handler,
            params=params,
            dry_run=dry_run,
            group="task",
            command_field="task_command",
            command_name=shortcut_name,
            steps=[{"action": f"task.{shortcut_name.replace('-', '_')}"}],
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


def _mail_p6_command(shortcut_name: str) -> click.Command:
    spec = get_shortcut(f"mail.+{shortcut_name}")
    assert spec is not None

    @click.command(name=f"+{shortcut_name}", help=spec.description)
    @click.option("--mailbox")
    @click.option("--user-mailbox-id")
    @click.option("--message-id")
    @click.option("--message-ids")
    @click.option("--thread-id")
    @click.option("--html", default="true", show_default=True)
    @click.option("--to")
    @click.option("--cc")
    @click.option("--bcc")
    @click.option("--subject")
    @click.option("--body")
    @click.option("--body-file")
    @click.option("--body-stdin", is_flag=True)
    @click.option("--from", "from_email")
    @click.option("--plain-text", is_flag=True)
    @click.option("--confirm-send", is_flag=True)
    @click.option("--send-time")
    @click.option("--request-receipt", is_flag=True)
    @click.option("--receive-id")
    @click.option("--receive-id-type", default="chat_id", show_default=True)
    @click.option("--detail")
    @click.option("--name")
    @click.option("--template-id")
    @click.option("--template-content")
    @click.option("--template-content-file")
    @click.option("--template-content-stdin", is_flag=True)
    @click.option("--set-name")
    @click.option("--set-subject")
    @click.option("--set-template-content")
    @click.option("--set-template-content-file")
    @click.option("--set-template-content-stdin", is_flag=True)
    @click.option("--set-plain-text", is_flag=True)
    @click.option("--set-to")
    @click.option("--set-cc")
    @click.option("--set-bcc")
    @click.option("--filter")
    @click.option("--query")
    @click.option("--max", "max_items", type=int)
    @click.option("--page-size", type=int)
    @click.option("--page-token")
    @click.option("--folder-id")
    @click.option("--labels", is_flag=True)
    @click.option("--msg-format", default="metadata", show_default=True)
    @click.option("--output-dir")
    @click.option("--labels-json")
    @click.option("--folders-json")
    @click.option("--label-ids-json")
    @click.option("--folder-ids-json")
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_mail_p6_shortcut,
            params=params,
            dry_run=dry_run,
            group="mail",
            command_field="mail_command",
            command_name=shortcut_name,
            steps=[{"action": f"mail.{shortcut_name.replace('-', '_')}"}],
        )

    return _command


def _okr_command(shortcut_name: str) -> click.Command:
    spec = get_shortcut(f"okr.+{shortcut_name}")
    assert spec is not None

    @click.command(name=f"+{shortcut_name}", help=spec.description)
    @click.option("--user-id")
    @click.option("--user-id-type", default="open_id", show_default=True)
    @click.option("--time-range")
    @click.option("--cycle-id")
    @click.option("--target-id")
    @click.option(
        "--target-type",
        type=click.Choice(["objective", "key_result"]),
    )
    @click.option("--department-id-type", default="open_department_id", show_default=True)
    @click.option("--progress-id")
    @click.option("--content")
    @click.option("--content-file")
    @click.option("--content-stdin", is_flag=True)
    @click.option("--progress-percent")
    @click.option(
        "--progress-status",
        type=click.Choice(["normal", "overdue", "done"]),
    )
    @click.option("--source-title", default="created by lark-cli", show_default=True)
    @click.option("--source-url")
    @click.option("--file", "file")
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_okr_shortcut,
            params=params,
            dry_run=dry_run,
            group="okr",
            command_field="okr_command",
            command_name=shortcut_name,
            steps=[{"action": f"okr.{shortcut_name.replace('-', '_')}"}],
        )

    return _command


def _base_command(shortcut_name: str) -> click.Command:
    spec = get_shortcut(f"base.+{shortcut_name}")
    assert spec is not None

    @click.command(name=f"+{shortcut_name}", help=spec.description)
    @click.option("--base-token")
    @click.option("--table-id")
    @click.option("--view-id")
    @click.option("--record-id")
    @click.option("--record-ids")
    @click.option("--role-id")
    @click.option("--workflow-id")
    @click.option("--form-id")
    @click.option("--question-id")
    @click.option("--dashboard-id")
    @click.option("--block-id")
    @click.option("--name")
    @click.option("--folder-token")
    @click.option("--time-zone")
    @click.option("--without-content", is_flag=True)
    @click.option("--offset", type=int, default=0, show_default=True)
    @click.option("--limit", type=int)
    @click.option("--page-size", type=int)
    @click.option("--page-token")
    @click.option("--max-version", type=int)
    @click.option("--field-id", "field_id", multiple=True)
    @click.option("--json")
    @click.option("--dsl")
    @click.option("--questions")
    @click.option("--description")
    @click.option("--status")
    @click.option("--keyword")
    @click.option("--theme-style")
    @click.option("--type", "block_type")
    @click.option("--data-config")
    @click.option("--user-id-type")
    @click.option("--file", "file")
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_base_shortcut,
            params=params,
            dry_run=dry_run,
            group="base",
            command_field="base_command",
            command_name=shortcut_name,
            steps=[{"action": f"base.{shortcut_name.replace('-', '_')}"}],
        )

    return _command


def _vc_search_command() -> click.Command:
    spec = get_shortcut("vc.+search")
    assert spec is not None

    @click.command(name="+search", help=spec.description)
    @click.option("--query")
    @click.option("--start")
    @click.option("--end")
    @click.option("--organizer-ids")
    @click.option("--participant-ids")
    @click.option("--room-ids")
    @click.option("--page-token")
    @click.option("--page-size", type=int, default=15, show_default=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_vc_search,
            params=params,
            dry_run=dry_run,
            group="vc",
            command_field="vc_command",
            command_name="search",
            steps=[{"action": "vc.meetings.search"}],
        )

    return _command


def _vc_notes_command() -> click.Command:
    spec = get_shortcut("vc.+notes")
    assert spec is not None

    @click.command(name="+notes", help=spec.description)
    @click.option("--meeting-ids")
    @click.option("--minute-tokens")
    @click.option("--calendar-event-ids")
    @click.option("--output-dir")
    @click.option("--overwrite", is_flag=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_vc_notes,
            params=params,
            dry_run=dry_run,
            group="vc",
            command_field="vc_command",
            command_name="notes",
            steps=[
                {"action": "vc.meetings.get", "optional": True},
                {"action": "vc.notes.get", "optional": True},
                {"action": "minutes.get", "optional": True},
                {"action": "calendar.event_relation_info", "optional": True},
            ],
        )

    return _command


def _vc_recording_command() -> click.Command:
    spec = get_shortcut("vc.+recording")
    assert spec is not None

    @click.command(name="+recording", help=spec.description)
    @click.option("--meeting-ids")
    @click.option("--calendar-event-ids")
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_vc_recording,
            params=params,
            dry_run=dry_run,
            group="vc",
            command_field="vc_command",
            command_name="recording",
            steps=[
                {"action": "vc.recording.get"},
                {"action": "calendar.event_relation_info", "optional": True},
            ],
        )

    return _command


def _wiki_move_command() -> click.Command:
    spec = get_shortcut("wiki.+move")
    assert spec is not None

    @click.command(name="+move", help=spec.description)
    @click.option("--node-token")
    @click.option("--source-space-id")
    @click.option("--target-space-id")
    @click.option("--target-parent-token")
    @click.option("--obj-type")
    @click.option("--obj-token")
    @click.option("--apply", is_flag=True)
    @click.option("--poll-attempts", type=int, default=30, show_default=True)
    @click.option("--poll-interval", type=float, default=2.0, show_default=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_wiki_move,
            params=params,
            dry_run=dry_run,
            group="wiki",
            command_field="wiki_command",
            command_name="move",
            steps=[
                {"action": "wiki.nodes.resolve", "optional": True},
                {"action": "wiki.nodes.move", "optional": True},
                {"action": "wiki.nodes.move_docs_to_wiki", "optional": True},
                {"action": "wiki.tasks.poll", "optional": True},
            ],
        )

    return _command


def _wiki_node_create_command() -> click.Command:
    spec = get_shortcut("wiki.+node-create")
    assert spec is not None

    @click.command(name="+node-create", help=spec.description)
    @click.option("--space-id")
    @click.option("--parent-node-token")
    @click.option("--title")
    @click.option("--node-type", default="origin", show_default=True)
    @click.option("--obj-type", default="docx", show_default=True)
    @click.option("--origin-node-token")
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_wiki_node_create,
            params=params,
            dry_run=dry_run,
            group="wiki",
            command_field="wiki_command",
            command_name="node-create",
            steps=[
                {"action": "wiki.spaces.resolve", "optional": True},
                {"action": "wiki.nodes.create"},
            ],
        )

    return _command


def _wiki_delete_space_command() -> click.Command:
    spec = get_shortcut("wiki.+delete-space")
    assert spec is not None

    @click.command(name="+delete-space", help=spec.description)
    @click.option("--space-id", required=True)
    @click.option("--poll-attempts", type=int, default=30, show_default=True)
    @click.option("--poll-interval", type=float, default=2.0, show_default=True)
    @click.option("--yes", is_flag=True)
    @click.option("--dry-run", is_flag=True)
    @with_runtime_options
    def _command(**kwargs: Any) -> None:
        cli_ctx, params = build_cli_context(kwargs)
        dry_run = bool(params.pop("dry_run", False))
        _invoke_shortcut(
            cli_ctx=cli_ctx,
            shortcut=spec,
            handler=_cmd_wiki_delete_space,
            params=params,
            dry_run=dry_run,
            group="wiki",
            command_field="wiki_command",
            command_name="delete-space",
            steps=[
                {"action": "wiki.spaces.delete"},
                {"action": "wiki.tasks.poll", "optional": True},
            ],
        )

    return _command


__all__ = [
    "ShortcutSpec",
    "attach_shortcuts",
    "get_shortcut",
    "list_shortcuts",
]
