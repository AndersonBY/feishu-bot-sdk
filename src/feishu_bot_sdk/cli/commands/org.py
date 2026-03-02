from __future__ import annotations

import argparse
from typing import Any, Mapping, Optional

from ...calendar import CalendarService
from ...contact import ContactService
from ...drive_files import DriveFileService

from ..runtime import (
    _build_client,
    _extract_response_data,
    _merge_calendar_attachment,
    _normalize_calendar_attachments,
    _parse_json_object,
)

def _cmd_calendar_primary(args: argparse.Namespace) -> Mapping[str, Any]:
    service = CalendarService(_build_client(args))
    return service.primary_calendar(user_id_type=getattr(args, "user_id_type", None))


def _cmd_calendar_list_calendars(args: argparse.Namespace) -> Mapping[str, Any]:
    service = CalendarService(_build_client(args))
    return service.list_calendars(
        page_size=getattr(args, "page_size", None),
        page_token=getattr(args, "page_token", None),
        sync_token=getattr(args, "sync_token", None),
    )


def _cmd_calendar_get_calendar(args: argparse.Namespace) -> Mapping[str, Any]:
    service = CalendarService(_build_client(args))
    return service.get_calendar(str(args.calendar_id))


def _cmd_calendar_create_calendar(args: argparse.Namespace) -> Mapping[str, Any]:
    calendar = _parse_json_object(
        json_text=getattr(args, "calendar_json", None),
        file_path=getattr(args, "calendar_file", None),
        stdin_enabled=bool(getattr(args, "calendar_stdin", False)),
        name="calendar",
        required=True,
    )
    service = CalendarService(_build_client(args))
    return service.create_calendar(calendar)


def _cmd_calendar_update_calendar(args: argparse.Namespace) -> Mapping[str, Any]:
    calendar = _parse_json_object(
        json_text=getattr(args, "calendar_json", None),
        file_path=getattr(args, "calendar_file", None),
        stdin_enabled=bool(getattr(args, "calendar_stdin", False)),
        name="calendar",
        required=True,
    )
    service = CalendarService(_build_client(args))
    return service.update_calendar(str(args.calendar_id), calendar)


def _cmd_calendar_delete_calendar(args: argparse.Namespace) -> Mapping[str, Any]:
    service = CalendarService(_build_client(args))
    return service.delete_calendar(str(args.calendar_id))


def _cmd_calendar_search_calendars(args: argparse.Namespace) -> Mapping[str, Any]:
    service = CalendarService(_build_client(args))
    return service.search_calendars(
        str(args.query),
        page_size=getattr(args, "page_size", None),
        page_token=getattr(args, "page_token", None),
    )


def _cmd_calendar_list_events(args: argparse.Namespace) -> Mapping[str, Any]:
    service = CalendarService(_build_client(args))
    return service.list_events(
        str(args.calendar_id),
        page_size=getattr(args, "page_size", None),
        page_token=getattr(args, "page_token", None),
        sync_token=getattr(args, "sync_token", None),
        start_time=getattr(args, "start_time", None),
        end_time=getattr(args, "end_time", None),
        anchor_time=getattr(args, "anchor_time", None),
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_calendar_get_event(args: argparse.Namespace) -> Mapping[str, Any]:
    service = CalendarService(_build_client(args))
    return service.get_event(
        str(args.calendar_id),
        str(args.event_id),
        need_meeting_settings=True if bool(getattr(args, "need_meeting_settings", False)) else None,
        need_attendee=True if bool(getattr(args, "need_attendee", False)) else None,
        max_attendee_num=getattr(args, "max_attendee_num", None),
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_calendar_create_event(args: argparse.Namespace) -> Mapping[str, Any]:
    event = _parse_json_object(
        json_text=getattr(args, "event_json", None),
        file_path=getattr(args, "event_file", None),
        stdin_enabled=bool(getattr(args, "event_stdin", False)),
        name="event",
        required=True,
    )
    service = CalendarService(_build_client(args))
    return service.create_event(
        str(args.calendar_id),
        event,
        user_id_type=getattr(args, "user_id_type", None),
        idempotency_key=getattr(args, "idempotency_key", None),
    )


def _cmd_calendar_update_event(args: argparse.Namespace) -> Mapping[str, Any]:
    event = _parse_json_object(
        json_text=getattr(args, "event_json", None),
        file_path=getattr(args, "event_file", None),
        stdin_enabled=bool(getattr(args, "event_stdin", False)),
        name="event",
        required=True,
    )
    service = CalendarService(_build_client(args))
    return service.update_event(
        str(args.calendar_id),
        str(args.event_id),
        event,
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_calendar_attach_material(args: argparse.Namespace) -> Mapping[str, Any]:
    calendar_id = str(args.calendar_id)
    event_id = str(args.event_id)
    mode = str(getattr(args, "mode", "append")).strip().lower()
    need_notification_raw = getattr(args, "need_notification", None)
    need_notification: Optional[bool]
    if need_notification_raw is None:
        need_notification = None
    else:
        need_notification = str(need_notification_raw).lower() == "true"

    client = _build_client(args)
    drive = DriveFileService(client)
    calendar = CalendarService(client)

    upload_result = drive.upload_media(
        str(args.path),
        parent_type="calendar",
        parent_node=calendar_id,
        file_name=getattr(args, "file_name", None),
        content_type=getattr(args, "content_type", None),
    )
    upload_data = _extract_response_data(upload_result)
    file_token_value = upload_data.get("file_token")
    if not isinstance(file_token_value, str) or not file_token_value:
        raise ValueError("upload material succeeded but file_token is missing in response")
    file_token = file_token_value

    attachments: list[dict[str, Any]] = []
    if mode == "append":
        event_result = calendar.get_event(
            calendar_id,
            event_id,
            user_id_type=getattr(args, "user_id_type", None),
        )
        event_data = _extract_response_data(event_result)
        event_payload = event_data.get("event")
        if isinstance(event_payload, Mapping):
            attachments = _normalize_calendar_attachments(event_payload.get("attachments"))

    attachment_name = upload_data.get("name")
    if not isinstance(attachment_name, str) or not attachment_name:
        attachment_name = getattr(args, "file_name", None)
    attachments = _merge_calendar_attachment(
        attachments,
        file_token=file_token,
        name=attachment_name,
    )

    event_payload: dict[str, object] = {"attachments": attachments}
    if need_notification is not None:
        event_payload["need_notification"] = need_notification

    update_result = calendar.update_event(
        calendar_id,
        event_id,
        event_payload,
        user_id_type=getattr(args, "user_id_type", None),
    )
    update_data = _extract_response_data(update_result)
    update_event_raw = update_data.get("event")
    updated_event_payload = (
        {str(key): value for key, value in update_event_raw.items()}
        if isinstance(update_event_raw, Mapping)
        else {}
    )

    return {
        "calendar_id": calendar_id,
        "event_id": event_id,
        "mode": mode,
        "file_token": file_token,
        "uploaded_name": attachment_name,
        "attachments_count": len(attachments),
        "attachments": attachments,
        "updated_event": updated_event_payload,
    }


def _cmd_calendar_delete_event(args: argparse.Namespace) -> Mapping[str, Any]:
    raw_need_notification = getattr(args, "need_notification", None)
    need_notification: Optional[bool]
    if raw_need_notification is None:
        need_notification = None
    else:
        need_notification = str(raw_need_notification).lower() == "true"
    service = CalendarService(_build_client(args))
    return service.delete_event(
        str(args.calendar_id),
        str(args.event_id),
        need_notification=need_notification,
    )


def _cmd_calendar_search_events(args: argparse.Namespace) -> Mapping[str, Any]:
    search_filter = _parse_json_object(
        json_text=getattr(args, "filter_json", None),
        file_path=getattr(args, "filter_file", None),
        stdin_enabled=bool(getattr(args, "filter_stdin", False)),
        name="filter",
        required=False,
    )
    service = CalendarService(_build_client(args))
    return service.search_events(
        str(args.calendar_id),
        str(args.query),
        page_size=getattr(args, "page_size", None),
        page_token=getattr(args, "page_token", None),
        user_id_type=getattr(args, "user_id_type", None),
        search_filter=search_filter or None,
    )


def _cmd_calendar_reply_event(args: argparse.Namespace) -> Mapping[str, Any]:
    reply = _parse_json_object(
        json_text=getattr(args, "reply_json", None),
        file_path=getattr(args, "reply_file", None),
        stdin_enabled=bool(getattr(args, "reply_stdin", False)),
        name="reply",
        required=True,
    )
    service = CalendarService(_build_client(args))
    return service.reply_event(str(args.calendar_id), str(args.event_id), reply)


def _cmd_calendar_list_freebusy(args: argparse.Namespace) -> Mapping[str, Any]:
    request = _parse_json_object(
        json_text=getattr(args, "request_json", None),
        file_path=getattr(args, "request_file", None),
        stdin_enabled=bool(getattr(args, "request_stdin", False)),
        name="request",
        required=True,
    )
    service = CalendarService(_build_client(args))
    return service.list_freebusy(request, user_id_type=getattr(args, "user_id_type", None))


def _cmd_calendar_batch_freebusy(args: argparse.Namespace) -> Mapping[str, Any]:
    request = _parse_json_object(
        json_text=getattr(args, "request_json", None),
        file_path=getattr(args, "request_file", None),
        stdin_enabled=bool(getattr(args, "request_stdin", False)),
        name="request",
        required=True,
    )
    service = CalendarService(_build_client(args))
    return service.batch_freebusy(request, user_id_type=getattr(args, "user_id_type", None))


def _cmd_calendar_generate_caldav_conf(args: argparse.Namespace) -> Mapping[str, Any]:
    request = _parse_json_object(
        json_text=getattr(args, "request_json", None),
        file_path=getattr(args, "request_file", None),
        stdin_enabled=bool(getattr(args, "request_stdin", False)),
        name="request",
        required=True,
    )
    service = CalendarService(_build_client(args))
    return service.generate_caldav_conf(request)


def _cmd_contact_user_get(args: argparse.Namespace) -> Mapping[str, Any]:
    service = ContactService(_build_client(args))
    return service.get_user(
        str(args.user_id),
        user_id_type=getattr(args, "user_id_type", None),
        department_id_type=getattr(args, "department_id_type", None),
    )


def _cmd_contact_user_batch_get(args: argparse.Namespace) -> Mapping[str, Any]:
    user_ids = list(getattr(args, "user_ids", []) or [])
    service = ContactService(_build_client(args))
    return service.batch_get_users(
        user_ids,
        user_id_type=getattr(args, "user_id_type", None),
        department_id_type=getattr(args, "department_id_type", None),
    )


def _cmd_contact_user_get_id(args: argparse.Namespace) -> Mapping[str, Any]:
    emails = list(getattr(args, "emails", []) or [])
    mobiles = list(getattr(args, "mobiles", []) or [])
    if not emails and not mobiles:
        raise ValueError("at least one of --email or --mobile is required")
    raw_include_resigned = getattr(args, "include_resigned", None)
    include_resigned: Optional[bool]
    if raw_include_resigned is None:
        include_resigned = None
    else:
        include_resigned = str(raw_include_resigned).lower() == "true"
    service = ContactService(_build_client(args))
    return service.batch_get_user_ids(
        emails=emails or None,
        mobiles=mobiles or None,
        include_resigned=include_resigned,
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_contact_user_by_department(args: argparse.Namespace) -> Mapping[str, Any]:
    service = ContactService(_build_client(args))
    return service.find_users_by_department(
        str(args.department_id),
        user_id_type=getattr(args, "user_id_type", None),
        department_id_type=getattr(args, "department_id_type", None),
        page_size=getattr(args, "page_size", None),
        page_token=getattr(args, "page_token", None),
    )


def _cmd_contact_user_search(args: argparse.Namespace) -> Mapping[str, Any]:
    service = ContactService(_build_client(args))
    return service.search_users(
        str(args.query),
        page_size=getattr(args, "page_size", None),
        page_token=getattr(args, "page_token", None),
    )


def _cmd_contact_department_get(args: argparse.Namespace) -> Mapping[str, Any]:
    service = ContactService(_build_client(args))
    return service.get_department(
        str(args.department_id),
        user_id_type=getattr(args, "user_id_type", None),
        department_id_type=getattr(args, "department_id_type", None),
    )


def _cmd_contact_department_children(args: argparse.Namespace) -> Mapping[str, Any]:
    raw_fetch_child = getattr(args, "fetch_child", None)
    fetch_child: Optional[bool]
    if raw_fetch_child is None:
        fetch_child = None
    else:
        fetch_child = str(raw_fetch_child).lower() == "true"
    service = ContactService(_build_client(args))
    return service.list_department_children(
        str(args.department_id),
        user_id_type=getattr(args, "user_id_type", None),
        department_id_type=getattr(args, "department_id_type", None),
        fetch_child=fetch_child,
        page_size=getattr(args, "page_size", None),
        page_token=getattr(args, "page_token", None),
    )


def _cmd_contact_department_batch_get(args: argparse.Namespace) -> Mapping[str, Any]:
    department_ids = list(getattr(args, "department_ids", []) or [])
    service = ContactService(_build_client(args))
    return service.batch_get_departments(
        department_ids,
        user_id_type=getattr(args, "user_id_type", None),
        department_id_type=getattr(args, "department_id_type", None),
    )


def _cmd_contact_department_parent(args: argparse.Namespace) -> Mapping[str, Any]:
    service = ContactService(_build_client(args))
    return service.list_parent_departments(
        str(args.department_id),
        user_id_type=getattr(args, "user_id_type", None),
        department_id_type=getattr(args, "department_id_type", None),
        page_size=getattr(args, "page_size", None),
        page_token=getattr(args, "page_token", None),
    )


def _cmd_contact_department_search(args: argparse.Namespace) -> Mapping[str, Any]:
    service = ContactService(_build_client(args))
    return service.search_departments(
        str(args.query),
        user_id_type=getattr(args, "user_id_type", None),
        department_id_type=getattr(args, "department_id_type", None),
        page_size=getattr(args, "page_size", None),
        page_token=getattr(args, "page_token", None),
    )


def _cmd_contact_scope_get(args: argparse.Namespace) -> Mapping[str, Any]:
    service = ContactService(_build_client(args))
    return service.list_scopes(
        user_id_type=getattr(args, "user_id_type", None),
        department_id_type=getattr(args, "department_id_type", None),
        page_size=getattr(args, "page_size", None),
        page_token=getattr(args, "page_token", None),
    )


__all__ = [name for name in globals() if name.startswith("_cmd_")]
