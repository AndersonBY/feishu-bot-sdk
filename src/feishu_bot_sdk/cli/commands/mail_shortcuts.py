from __future__ import annotations

import argparse
from typing import Any, Mapping

from ...mail import MailDraftService, MailThreadService
from ..runtime import _build_client, _resolve_text_input


def _cmd_mail_draft_create(args: argparse.Namespace) -> Mapping[str, Any]:
    raw = _resolve_text_input(
        text=getattr(args, "raw", None),
        file_path=getattr(args, "raw_file", None),
        stdin_enabled=bool(getattr(args, "raw_stdin", False)),
        name="raw",
    )
    service = MailDraftService(_build_client(args))
    return service.create_draft(str(args.user_mailbox_id), {"raw": raw})


def _cmd_mail_draft_edit(args: argparse.Namespace) -> Mapping[str, Any]:
    raw = _resolve_text_input(
        text=getattr(args, "raw", None),
        file_path=getattr(args, "raw_file", None),
        stdin_enabled=bool(getattr(args, "raw_stdin", False)),
        name="raw",
    )
    service = MailDraftService(_build_client(args))
    return service.update_draft(str(args.user_mailbox_id), str(args.draft_id), {"raw": raw})


def _cmd_mail_thread(args: argparse.Namespace) -> Mapping[str, Any]:
    service = MailThreadService(_build_client(args))
    return service.get_thread(
        str(args.user_mailbox_id),
        str(args.thread_id),
        format=getattr(args, "thread_format", None),
        include_spam_trash=True if bool(getattr(args, "include_spam_trash", False)) else None,
    )


__all__ = [
    "_cmd_mail_draft_create",
    "_cmd_mail_draft_edit",
    "_cmd_mail_thread",
]
