from __future__ import annotations

import argparse
import json
from typing import Any, Mapping

from ...mail import MailDraftService, MailThreadService
from ..runtime import _build_client, _resolve_text_input


READ_RECEIPT_REQUEST_LABEL = "READ_RECEIPT_REQUEST"


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


def _cmd_mail_p6_shortcut(args: argparse.Namespace) -> Mapping[str, Any]:
    command = str(getattr(args, "mail_command", "") or "")
    if command == "message":
        return _cmd_mail_message(args)
    if command == "messages":
        return _cmd_mail_messages(args)
    if command == "send":
        return _cmd_mail_compose(args, mode="send")
    if command == "reply":
        return _cmd_mail_compose(args, mode="reply")
    if command == "reply-all":
        return _cmd_mail_compose(args, mode="reply-all")
    if command == "forward":
        return _cmd_mail_compose(args, mode="forward")
    if command == "send-receipt":
        return _cmd_mail_send_receipt(args)
    if command == "decline-receipt":
        return _cmd_mail_decline_receipt(args)
    if command == "share-to-chat":
        return _cmd_mail_share_to_chat(args)
    if command == "signature":
        return _cmd_mail_signature(args)
    if command == "template-create":
        return _cmd_mail_template_create(args)
    if command == "template-update":
        return _cmd_mail_template_update(args)
    if command == "triage":
        return _cmd_mail_triage(args)
    if command == "watch":
        return _cmd_mail_watch(args)
    raise ValueError(f"unsupported mail shortcut: {command}")


def _cmd_mail_message(args: argparse.Namespace) -> Mapping[str, Any]:
    mailbox = _mailbox(args)
    message_id = _required_string(getattr(args, "message_id", None), name="message-id")
    response = _build_client(args).request_json(
        "GET",
        f"/mail/v1/user_mailboxes/{mailbox}/messages/{message_id}",
        params={"format": _message_format(args)},
    )
    return _data_or_raw(response)


def _cmd_mail_messages(args: argparse.Namespace) -> Mapping[str, Any]:
    mailbox = _mailbox(args)
    message_ids = _split_csv(getattr(args, "message_ids", None))
    if not message_ids:
        raise ValueError("at least one --message-ids value is required")
    response = _build_client(args).request_json(
        "POST",
        f"/mail/v1/user_mailboxes/{mailbox}/messages/batch_get",
        payload={"message_ids": message_ids, "format": _message_format(args)},
    )
    return _data_or_raw(response)


def _cmd_mail_compose(args: argparse.Namespace, *, mode: str) -> Mapping[str, Any]:
    mailbox = _mailbox(args)
    payload = _compose_payload(args)
    if mode == "reply":
        payload["reply_to_message_id"] = _required_string(getattr(args, "message_id", None), name="message-id")
    elif mode == "reply-all":
        payload["reply_to_message_id"] = _required_string(getattr(args, "message_id", None), name="message-id")
        payload["reply_all"] = True
    elif mode == "forward":
        payload["forward_message_id"] = _required_string(getattr(args, "message_id", None), name="message-id")
    elif mode != "send":
        raise ValueError(f"unsupported compose mode: {mode}")

    client = _build_client(args)
    create_response = client.request_json(
        "POST",
        f"/mail/v1/user_mailboxes/{mailbox}/drafts",
        payload=payload,
    )
    create_data = _data_or_raw(create_response)
    if not bool(getattr(args, "confirm_send", False)):
        return create_data

    draft_id = _extract_draft_id(create_data)
    if not draft_id:
        raise ValueError("draft create response did not include draft_id")
    send_payload: dict[str, Any] = {}
    send_time = _optional_string(getattr(args, "send_time", None))
    if send_time:
        send_payload["send_time"] = send_time
    send_response = client.request_json(
        "POST",
        f"/mail/v1/user_mailboxes/{mailbox}/drafts/{draft_id}/send",
        payload=send_payload,
    )
    return {"draft": create_data, "send": _data_or_raw(send_response)}


def _cmd_mail_send_receipt(args: argparse.Namespace) -> Mapping[str, Any]:
    mailbox = _mailbox(args)
    message_id = _required_string(getattr(args, "message_id", None), name="message-id")
    client = _build_client(args)
    message_data = _data_or_raw(
        client.request_json(
            "GET",
            f"/mail/v1/user_mailboxes/{mailbox}/messages/{message_id}",
            params={"format": "metadata"},
        )
    )
    message = message_data.get("message")
    message_map = message if isinstance(message, Mapping) else message_data
    if not _has_read_receipt_request_label(message_map):
        raise ValueError(f"message {message_id} did not request a read receipt")
    payload = {
        "read_receipt_message_id": message_id,
        "head_from": _head_from(getattr(args, "from_email", None)),
    }
    payload = _drop_empty(payload)
    create_response = client.request_json("POST", f"/mail/v1/user_mailboxes/{mailbox}/drafts", payload=payload)
    create_data = _data_or_raw(create_response)
    draft_id = _extract_draft_id(create_data)
    if not draft_id:
        raise ValueError("draft create response did not include draft_id")
    send_response = client.request_json(
        "POST",
        f"/mail/v1/user_mailboxes/{mailbox}/drafts/{draft_id}/send",
        payload={},
    )
    return {"draft": create_data, "send": _data_or_raw(send_response)}


def _cmd_mail_decline_receipt(args: argparse.Namespace) -> Mapping[str, Any]:
    mailbox = _mailbox(args)
    message_id = _required_string(getattr(args, "message_id", None), name="message-id")
    response = _build_client(args).request_json(
        "PUT",
        f"/mail/v1/user_mailboxes/{mailbox}/messages/{message_id}/modify",
        payload={"remove_label_ids": [READ_RECEIPT_REQUEST_LABEL]},
    )
    return _data_or_raw(response)


def _has_read_receipt_request_label(message: Mapping[str, Any]) -> bool:
    raw_labels = message.get("label_ids")
    if not isinstance(raw_labels, list):
        raw_labels = message.get("labels")
    if not isinstance(raw_labels, list):
        return False
    labels = {str(item) for item in raw_labels if item is not None}
    return READ_RECEIPT_REQUEST_LABEL in labels or "-607" in labels


def _cmd_mail_share_to_chat(args: argparse.Namespace) -> Mapping[str, Any]:
    mailbox = _mailbox(args)
    message_id = _optional_string(getattr(args, "message_id", None))
    thread_id = _optional_string(getattr(args, "thread_id", None))
    if bool(message_id) == bool(thread_id):
        raise ValueError("exactly one of --message-id or --thread-id is required")
    receive_id = _required_string(getattr(args, "receive_id", None), name="receive-id")
    receive_id_type = _optional_string(getattr(args, "receive_id_type", None)) or "chat_id"
    create_payload = {"thread_id": thread_id} if thread_id else {"message_id": message_id}
    client = _build_client(args)
    create_data = _data_or_raw(
        client.request_json(
            "POST",
            f"/mail/v1/user_mailboxes/{mailbox}/messages/share_token",
            payload=create_payload,
        )
    )
    card_id = _optional_string(create_data.get("card_id"))
    if not card_id:
        raise ValueError("share token response did not include card_id")
    send_data = _data_or_raw(
        client.request_json(
            "POST",
            f"/mail/v1/user_mailboxes/{mailbox}/share_tokens/{card_id}/send",
            params={"receive_id_type": receive_id_type},
            payload={"receive_id": receive_id},
        )
    )
    return {"card_id": card_id, "im_message_id": send_data.get("message_id"), "send": send_data}


def _cmd_mail_signature(args: argparse.Namespace) -> Mapping[str, Any]:
    mailbox = _optional_string(getattr(args, "from_email", None)) or _mailbox(args)
    data = _data_or_raw(
        _build_client(args).request_json(
            "GET",
            f"/mail/v1/user_mailboxes/{mailbox}/signatures",
        )
    )
    detail_id = _optional_string(getattr(args, "detail", None))
    if not detail_id:
        return data
    signatures = data.get("signatures")
    if isinstance(signatures, list):
        for item in signatures:
            if isinstance(item, Mapping) and str(item.get("id") or item.get("signature_id") or "") == detail_id:
                return {"signature": dict(item)}
    return {"signature": None, "signature_id": detail_id, "signatures": signatures if isinstance(signatures, list) else []}


def _cmd_mail_template_create(args: argparse.Namespace) -> Mapping[str, Any]:
    mailbox = _mailbox(args)
    name = _required_string(getattr(args, "name", None), name="name")
    content = _optional_text_input(
        text=getattr(args, "template_content", None),
        file_path=getattr(args, "template_content_file", None),
        stdin_enabled=bool(getattr(args, "template_content_stdin", False)),
        name="template-content",
    )
    payload = {
        "name": name,
        "subject": _optional_string(getattr(args, "subject", None)),
        "template_content": content or "",
        "tos": _recipients(getattr(args, "to", None)),
        "ccs": _recipients(getattr(args, "cc", None)),
        "bccs": _recipients(getattr(args, "bcc", None)),
        "attachments": [],
        "is_plain_text_mode": bool(getattr(args, "plain_text", False)),
    }
    response = _build_client(args).request_json(
        "POST",
        f"/mail/v1/user_mailboxes/{mailbox}/templates",
        payload=payload,
    )
    return _data_or_raw(response)


def _cmd_mail_template_update(args: argparse.Namespace) -> Mapping[str, Any]:
    mailbox = _mailbox(args)
    template_id = _required_string(getattr(args, "template_id", None), name="template-id")
    payload: dict[str, Any] = {}
    _set_if_present(payload, "name", getattr(args, "set_name", None))
    _set_if_present(payload, "subject", getattr(args, "set_subject", None))
    content = _optional_text_input(
        text=getattr(args, "set_template_content", None),
        file_path=getattr(args, "set_template_content_file", None),
        stdin_enabled=bool(getattr(args, "set_template_content_stdin", False)),
        name="set-template-content",
    )
    if content is not None:
        payload["template_content"] = content
    if bool(getattr(args, "set_plain_text", False)):
        payload["is_plain_text_mode"] = True
    for attr_name, field_name in (("set_to", "tos"), ("set_cc", "ccs"), ("set_bcc", "bccs")):
        value = getattr(args, attr_name, None)
        if value is not None:
            payload[field_name] = _recipients(value)
    if not payload:
        raise ValueError("at least one template update flag is required")
    response = _build_client(args).request_json(
        "PUT",
        f"/mail/v1/user_mailboxes/{mailbox}/templates/{template_id}",
        payload=payload,
    )
    return _data_or_raw(response)


def _cmd_mail_triage(args: argparse.Namespace) -> Mapping[str, Any]:
    mailbox = _mailbox(args)
    query = _optional_string(getattr(args, "query", None))
    filter_payload = _filter_payload(getattr(args, "filter", None))
    page_size = int(getattr(args, "page_size", None) or getattr(args, "max_items", None) or 20)
    page_token = _optional_string(getattr(args, "page_token", None))
    client = _build_client(args)
    if query or filter_payload:
        payload: dict[str, Any] = {"page_size": page_size}
        if query:
            payload["query"] = query
        if filter_payload:
            payload["filter"] = filter_payload
        if page_token:
            payload["page_token"] = page_token
        if bool(getattr(args, "labels", False)):
            payload["include_label_ids"] = True
        data = _data_or_raw(
            client.request_json(
                "POST",
                f"/mail/v1/user_mailboxes/{mailbox}/search",
                payload=payload,
            )
        )
        return _triage_output(data)

    params: dict[str, Any] = {
        "folder_id": _optional_string(getattr(args, "folder_id", None)) or "INBOX",
        "page_size": page_size,
    }
    if page_token:
        params["page_token"] = page_token
    data = _data_or_raw(
        client.request_json(
            "GET",
            f"/mail/v1/user_mailboxes/{mailbox}/messages",
            params=params,
        )
    )
    return _triage_output(data)


def _cmd_mail_watch(args: argparse.Namespace) -> Mapping[str, Any]:
    mailbox = _mailbox(args)
    data = _data_or_raw(
        _build_client(args).request_json(
            "POST",
            f"/mail/v1/user_mailboxes/{mailbox}/event/subscribe",
            payload={"event_type": 1},
        )
    )
    watch = {
        "mailbox": mailbox,
        "msg_format": _optional_string(getattr(args, "msg_format", None)) or "metadata",
        "output_dir": _optional_string(getattr(args, "output_dir", None)),
        "filters": _drop_empty(
            {
                "labels": _json_array_or_none(getattr(args, "labels_json", None)),
                "folders": _json_array_or_none(getattr(args, "folders_json", None)),
                "label_ids": _json_array_or_none(getattr(args, "label_ids_json", None)),
                "folder_ids": _json_array_or_none(getattr(args, "folder_ids_json", None)),
            }
        ),
        "note": "Subscribed to mail events. Live WebSocket streaming is not started by this shortcut implementation.",
    }
    return {"watch": _drop_empty(watch), "subscription": data}


def _mailbox(args: argparse.Namespace) -> str:
    value = (
        _optional_string(getattr(args, "mailbox", None))
        or _optional_string(getattr(args, "user_mailbox_id", None))
        or _optional_string(getattr(args, "from_email", None))
        or "me"
    )
    return value


def _message_format(args: argparse.Namespace) -> str:
    return "full" if _bool_value(getattr(args, "html", True), default=True) else "plain_text_full"


def _compose_payload(args: argparse.Namespace) -> dict[str, Any]:
    body = _optional_text_input(
        text=getattr(args, "body", None),
        file_path=getattr(args, "body_file", None),
        stdin_enabled=bool(getattr(args, "body_stdin", False)),
        name="body",
    )
    payload: dict[str, Any] = {
        "subject": _optional_string(getattr(args, "subject", None)),
        "to": _recipients(getattr(args, "to", None)),
        "cc": _recipients(getattr(args, "cc", None)),
        "bcc": _recipients(getattr(args, "bcc", None)),
        "head_from": _head_from(getattr(args, "from_email", None)),
    }
    if body is not None:
        body_field = "body_plain_text" if bool(getattr(args, "plain_text", False)) or not _looks_like_html(body) else "body_html"
        payload[body_field] = body
    if bool(getattr(args, "request_receipt", False)):
        payload["request_read_receipt"] = True
    return _drop_empty(payload)


def _optional_text_input(
    *,
    text: str | None,
    file_path: str | None,
    stdin_enabled: bool,
    name: str,
) -> str | None:
    source_count = int(bool(text)) + int(bool(file_path)) + int(bool(stdin_enabled))
    if source_count > 1:
        raise ValueError(f"only one of --{name}, --{name}-file or --{name}-stdin can be used")
    if source_count == 0:
        return None
    return _resolve_text_input(text=text, file_path=file_path, stdin_enabled=stdin_enabled, name=name)


def _recipients(value: Any) -> list[dict[str, str]]:
    return [{"mail_address": item} for item in _split_csv(value)]


def _head_from(value: Any) -> dict[str, str] | None:
    text = _optional_string(value)
    if not text:
        return None
    return {"mail_address": text}


def _split_csv(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        parts: list[str] = []
        for item in value:
            parts.extend(_split_csv(item))
        return parts
    return [item.strip() for item in str(value).split(",") if item.strip()]


def _filter_payload(value: Any) -> dict[str, Any]:
    text = _optional_string(value)
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"filter is not valid JSON: {exc}") from exc
    if not isinstance(parsed, Mapping):
        raise ValueError("filter must be a JSON object")
    return {str(key): item for key, item in parsed.items()}


def _json_array_or_none(value: Any) -> list[Any] | None:
    text = _optional_string(value)
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"expected JSON array: {exc}") from exc
    if not isinstance(parsed, list):
        raise ValueError("expected JSON array")
    return parsed


def _data_or_raw(response: Mapping[str, Any]) -> dict[str, Any]:
    data = response.get("data")
    if isinstance(data, Mapping):
        return {str(key): value for key, value in data.items()}
    return {str(key): value for key, value in response.items()}


def _extract_draft_id(data: Mapping[str, Any]) -> str | None:
    draft = data.get("draft")
    if isinstance(draft, Mapping):
        return _optional_string(draft.get("draft_id") or draft.get("id"))
    return _optional_string(data.get("draft_id") or data.get("id"))


def _required_string(value: Any, *, name: str) -> str:
    text = _optional_string(value)
    if not text:
        raise ValueError(f"--{name} is required")
    return text


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _bool_value(value: Any, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _looks_like_html(value: str) -> bool:
    return "<" in value and ">" in value


def _set_if_present(payload: dict[str, Any], field: str, value: Any) -> None:
    if value is not None:
        payload[field] = value


def _drop_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        str(key): value
        for key, value in payload.items()
        if value is not None and value != [] and value != {}
    }


def _triage_output(data: Mapping[str, Any]) -> dict[str, Any]:
    items = data.get("items")
    if not isinstance(items, list):
        messages = data.get("messages")
        items = messages if isinstance(messages, list) else []
    return {
        "items": items,
        "count": len(items),
        "has_more": bool(data.get("has_more")),
        "page_token": data.get("page_token"),
    }


__all__ = [
    "_cmd_mail_draft_create",
    "_cmd_mail_draft_edit",
    "_cmd_mail_p6_shortcut",
    "_cmd_mail_thread",
]
