from __future__ import annotations

import argparse

from ..commands import (
    _cmd_calendar_attach_material,
    _cmd_calendar_batch_freebusy,
    _cmd_calendar_create_calendar,
    _cmd_calendar_create_event,
    _cmd_calendar_delete_calendar,
    _cmd_calendar_delete_event,
    _cmd_calendar_generate_caldav_conf,
    _cmd_calendar_get_calendar,
    _cmd_calendar_get_event,
    _cmd_calendar_list_calendars,
    _cmd_calendar_list_events,
    _cmd_calendar_list_freebusy,
    _cmd_calendar_primary,
    _cmd_calendar_reply_event,
    _cmd_calendar_search_calendars,
    _cmd_calendar_search_events,
    _cmd_calendar_update_calendar,
    _cmd_calendar_update_event,
    _cmd_contact_department_batch_get,
    _cmd_contact_department_children,
    _cmd_contact_department_get,
    _cmd_contact_department_parent,
    _cmd_contact_department_search,
    _cmd_contact_scope_get,
    _cmd_contact_user_batch_get,
    _cmd_contact_user_by_department,
    _cmd_contact_user_get,
    _cmd_contact_user_get_id,
    _cmd_contact_user_search,
)
from ..settings import HELP_FORMATTER as _HELP_FORMATTER

def _build_calendar_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    shared: argparse.ArgumentParser,
) -> None:
    calendar_parser = subparsers.add_parser(
        "calendar",
        help="Calendar operations",
        description=(
            "Calendar operations.\n"
            "Tip: for event attachments, prefer `calendar attach-material` "
            "to avoid attachment token permission issues."
        ),
        formatter_class=_HELP_FORMATTER,
        epilog=(
            "Examples:\n"
            "  feishu calendar primary --auth-mode user --format json\n"
            "  feishu calendar create-event --auth-mode user --calendar-id <id> --event-file event.json --format json"
        ),
    )
    calendar_sub = calendar_parser.add_subparsers(dest="calendar_command")
    calendar_sub.required = True

    primary = calendar_sub.add_parser("primary", help="Get primary calendar", parents=[shared])
    primary.add_argument("--user-id-type", help="Optional user_id_type")
    primary.set_defaults(handler=_cmd_calendar_primary)

    list_calendars = calendar_sub.add_parser("list-calendars", help="List calendars", parents=[shared])
    list_calendars.add_argument("--page-size", type=int, help="Page size")
    list_calendars.add_argument("--page-token", help="Page token")
    list_calendars.add_argument("--sync-token", help="Sync token")
    list_calendars.set_defaults(handler=_cmd_calendar_list_calendars)

    get_calendar = calendar_sub.add_parser("get-calendar", help="Get calendar by id", parents=[shared])
    get_calendar.add_argument("--calendar-id", required=True, help="Calendar id")
    get_calendar.set_defaults(handler=_cmd_calendar_get_calendar)

    create_calendar = calendar_sub.add_parser("create-calendar", help="Create calendar", parents=[shared])
    create_calendar.add_argument("--calendar-json", help="Calendar JSON object string")
    create_calendar.add_argument("--calendar-file", help="Calendar JSON file path")
    create_calendar.add_argument("--calendar-stdin", action="store_true", help="Read calendar JSON from stdin")
    create_calendar.set_defaults(handler=_cmd_calendar_create_calendar)

    update_calendar = calendar_sub.add_parser("update-calendar", help="Update calendar", parents=[shared])
    update_calendar.add_argument("--calendar-id", required=True, help="Calendar id")
    update_calendar.add_argument("--calendar-json", help="Calendar JSON object string")
    update_calendar.add_argument("--calendar-file", help="Calendar JSON file path")
    update_calendar.add_argument("--calendar-stdin", action="store_true", help="Read calendar JSON from stdin")
    update_calendar.set_defaults(handler=_cmd_calendar_update_calendar)

    delete_calendar = calendar_sub.add_parser("delete-calendar", help="Delete calendar", parents=[shared])
    delete_calendar.add_argument("--calendar-id", required=True, help="Calendar id")
    delete_calendar.set_defaults(handler=_cmd_calendar_delete_calendar)

    search_calendars = calendar_sub.add_parser("search-calendars", help="Search calendars", parents=[shared])
    search_calendars.add_argument("--query", required=True, help="Search query")
    search_calendars.add_argument("--page-size", type=int, help="Page size")
    search_calendars.add_argument("--page-token", help="Page token")
    search_calendars.set_defaults(handler=_cmd_calendar_search_calendars)

    list_events = calendar_sub.add_parser("list-events", help="List events in a calendar", parents=[shared])
    list_events.add_argument("--calendar-id", required=True, help="Calendar id")
    list_events.add_argument("--page-size", type=int, help="Page size")
    list_events.add_argument("--page-token", help="Page token")
    list_events.add_argument("--sync-token", help="Sync token")
    list_events.add_argument("--start-time", help="Start time (unix seconds)")
    list_events.add_argument("--end-time", help="End time (unix seconds)")
    list_events.add_argument("--anchor-time", help="Anchor time (unix seconds)")
    list_events.add_argument("--user-id-type", help="Optional user_id_type")
    list_events.set_defaults(handler=_cmd_calendar_list_events)

    get_event = calendar_sub.add_parser("get-event", help="Get event by id", parents=[shared])
    get_event.add_argument("--calendar-id", required=True, help="Calendar id")
    get_event.add_argument("--event-id", required=True, help="Event id")
    get_event.add_argument("--need-attendee", action="store_true", help="Include attendees")
    get_event.add_argument("--need-meeting-settings", action="store_true", help="Include meeting settings")
    get_event.add_argument("--max-attendee-num", type=int, help="Max attendee count")
    get_event.add_argument("--user-id-type", help="Optional user_id_type")
    get_event.set_defaults(handler=_cmd_calendar_get_event)

    create_event = calendar_sub.add_parser(
        "create-event",
        help="Create event",
        parents=[shared],
        description=(
            "Create a calendar event on specified calendar_id.\n"
            "Payload must include at least summary/start_time/end_time."
        ),
        formatter_class=_HELP_FORMATTER,
        epilog=(
            "event.json example:\n"
            "  {\n"
            "    \"summary\": \"1:1 sync\",\n"
            "    \"description\": \"created by feishu cli\",\n"
            "    \"start_time\": {\"timestamp\": \"1772475902\"},\n"
            "    \"end_time\": {\"timestamp\": \"1772479502\"}\n"
            "  }\n"
            "\n"
            "Command:\n"
            "  feishu calendar create-event --auth-mode user --calendar-id <id> --event-file event.json --format json"
        ),
    )
    create_event.add_argument("--calendar-id", required=True, help="Calendar id")
    create_event.add_argument("--event-json", help="Event JSON object string")
    create_event.add_argument("--event-file", help="Event JSON file path")
    create_event.add_argument("--event-stdin", action="store_true", help="Read event JSON from stdin")
    create_event.add_argument("--user-id-type", help="Optional user_id_type")
    create_event.add_argument("--idempotency-key", help="Optional idempotency key")
    create_event.set_defaults(handler=_cmd_calendar_create_event)

    update_event = calendar_sub.add_parser("update-event", help="Update event", parents=[shared])
    update_event.add_argument("--calendar-id", required=True, help="Calendar id")
    update_event.add_argument("--event-id", required=True, help="Event id")
    update_event.add_argument("--event-json", help="Event JSON object string")
    update_event.add_argument("--event-file", help="Event JSON file path")
    update_event.add_argument("--event-stdin", action="store_true", help="Read event JSON from stdin")
    update_event.add_argument("--user-id-type", help="Optional user_id_type")
    update_event.set_defaults(handler=_cmd_calendar_update_event)

    attach_material = calendar_sub.add_parser(
        "attach-material",
        help="Upload a file as calendar material and attach to event",
        parents=[shared],
        description=(
            "Upload material for a calendar event and update event attachments.\n"
            "This command auto uses `parent_type=calendar` and `parent_node=<calendar_id>` "
            "when uploading media."
        ),
    )
    attach_material.add_argument("--calendar-id", required=True, help="Calendar id")
    attach_material.add_argument("--event-id", required=True, help="Event id")
    attach_material.add_argument("--path", required=True, help="Local file path to upload")
    attach_material.add_argument("--file-name", help="Override uploaded file name")
    attach_material.add_argument("--content-type", help="Override file content type")
    attach_material.add_argument(
        "--mode",
        choices=("append", "replace"),
        default="append",
        help="append keeps existing attachments; replace overwrites all (default: append)",
    )
    attach_material.add_argument(
        "--need-notification",
        choices=("true", "false"),
        help="Whether to notify attendees on update",
    )
    attach_material.add_argument("--user-id-type", help="Optional user_id_type")
    attach_material.set_defaults(handler=_cmd_calendar_attach_material)

    delete_event = calendar_sub.add_parser("delete-event", help="Delete event", parents=[shared])
    delete_event.add_argument("--calendar-id", required=True, help="Calendar id")
    delete_event.add_argument("--event-id", required=True, help="Event id")
    delete_event.add_argument(
        "--need-notification",
        choices=("true", "false"),
        help="Whether to notify attendees",
    )
    delete_event.set_defaults(handler=_cmd_calendar_delete_event)

    search_events = calendar_sub.add_parser("search-events", help="Search events in a calendar", parents=[shared])
    search_events.add_argument("--calendar-id", required=True, help="Calendar id")
    search_events.add_argument("--query", required=True, help="Search query")
    search_events.add_argument("--filter-json", help="Search filter JSON object string")
    search_events.add_argument("--filter-file", help="Search filter JSON file path")
    search_events.add_argument("--filter-stdin", action="store_true", help="Read search filter JSON from stdin")
    search_events.add_argument("--page-size", type=int, help="Page size")
    search_events.add_argument("--page-token", help="Page token")
    search_events.add_argument("--user-id-type", help="Optional user_id_type")
    search_events.set_defaults(handler=_cmd_calendar_search_events)

    reply_event = calendar_sub.add_parser("reply-event", help="Reply to an event", parents=[shared])
    reply_event.add_argument("--calendar-id", required=True, help="Calendar id")
    reply_event.add_argument("--event-id", required=True, help="Event id")
    reply_event.add_argument("--reply-json", help="Reply JSON object string")
    reply_event.add_argument("--reply-file", help="Reply JSON file path")
    reply_event.add_argument("--reply-stdin", action="store_true", help="Read reply JSON from stdin")
    reply_event.set_defaults(handler=_cmd_calendar_reply_event)

    freebusy = calendar_sub.add_parser("list-freebusy", help="Query freebusy", parents=[shared])
    freebusy.add_argument("--request-json", help="Request JSON object string")
    freebusy.add_argument("--request-file", help="Request JSON file path")
    freebusy.add_argument("--request-stdin", action="store_true", help="Read request JSON from stdin")
    freebusy.add_argument("--user-id-type", help="Optional user_id_type")
    freebusy.set_defaults(handler=_cmd_calendar_list_freebusy)

    batch_freebusy = calendar_sub.add_parser("batch-freebusy", help="Query freebusy in batch", parents=[shared])
    batch_freebusy.add_argument("--request-json", help="Request JSON object string")
    batch_freebusy.add_argument("--request-file", help="Request JSON file path")
    batch_freebusy.add_argument("--request-stdin", action="store_true", help="Read request JSON from stdin")
    batch_freebusy.add_argument("--user-id-type", help="Optional user_id_type")
    batch_freebusy.set_defaults(handler=_cmd_calendar_batch_freebusy)

    caldav = calendar_sub.add_parser("generate-caldav-conf", help="Generate CalDAV config", parents=[shared])
    caldav.add_argument("--request-json", help="Request JSON object string")
    caldav.add_argument("--request-file", help="Request JSON file path")
    caldav.add_argument("--request-stdin", action="store_true", help="Read request JSON from stdin")
    caldav.set_defaults(handler=_cmd_calendar_generate_caldav_conf)

def _build_contact_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    shared: argparse.ArgumentParser,
) -> None:
    contact_parser = subparsers.add_parser(
        "contact",
        help="Contact (address-book) operations",
        description=(
            "Contact / address-book operations.\n"
            "Some APIs require user auth and specific scopes."
        ),
        formatter_class=_HELP_FORMATTER,
        epilog=(
            "Examples:\n"
            "  feishu contact user get --user-id <open_id> --user-id-type open_id --auth-mode user --format json\n"
            "  feishu contact user search --query \"name\" --auth-mode user --format json"
        ),
    )
    contact_sub = contact_parser.add_subparsers(dest="contact_command")
    contact_sub.required = True

    user_parser = contact_sub.add_parser("user", help="User operations")
    user_sub = user_parser.add_subparsers(dest="contact_user_command")
    user_sub.required = True

    user_get = user_sub.add_parser(
        "get",
        help="Get user by id",
        parents=[shared],
        description=(
            "Get single user profile by user id/open_id/union_id.\n"
            "Typical user scope: contact:contact.base:readonly"
        ),
        formatter_class=_HELP_FORMATTER,
    )
    user_get.add_argument("--user-id", required=True, help="User id")
    user_get.add_argument("--user-id-type", help="Optional user_id_type")
    user_get.add_argument("--department-id-type", help="Optional department_id_type")
    user_get.set_defaults(handler=_cmd_contact_user_get)

    user_batch_get = user_sub.add_parser("batch-get", help="Batch get users by ids", parents=[shared])
    user_batch_get.add_argument(
        "--user-id",
        action="append",
        dest="user_ids",
        required=True,
        help="User id, repeatable",
    )
    user_batch_get.add_argument("--user-id-type", help="Optional user_id_type")
    user_batch_get.add_argument("--department-id-type", help="Optional department_id_type")
    user_batch_get.set_defaults(handler=_cmd_contact_user_batch_get)

    user_get_id = user_sub.add_parser(
        "get-id",
        help="Batch get user ids by emails/mobiles",
        parents=[shared],
    )
    user_get_id.add_argument("--email", action="append", dest="emails", help="Email, repeatable")
    user_get_id.add_argument("--mobile", action="append", dest="mobiles", help="Mobile, repeatable")
    user_get_id.add_argument(
        "--include-resigned",
        choices=("true", "false"),
        help="Include resigned users",
    )
    user_get_id.add_argument("--user-id-type", help="Optional user_id_type")
    user_get_id.set_defaults(handler=_cmd_contact_user_get_id)

    user_by_department = user_sub.add_parser(
        "by-department",
        help="List direct users in department",
        parents=[shared],
    )
    user_by_department.add_argument("--department-id", required=True, help="Department id")
    user_by_department.add_argument("--user-id-type", help="Optional user_id_type")
    user_by_department.add_argument("--department-id-type", help="Optional department_id_type")
    user_by_department.add_argument("--page-size", type=int, help="Page size")
    user_by_department.add_argument("--page-token", help="Page token")
    user_by_department.set_defaults(handler=_cmd_contact_user_by_department)

    user_search = user_sub.add_parser(
        "search",
        help="Search users (requires user access token)",
        parents=[shared],
        description=(
            "Search users by keyword.\n"
            "Requires user auth and scope: contact:user:search"
        ),
        formatter_class=_HELP_FORMATTER,
        epilog=(
            "Example:\n"
            "  feishu contact user search --query \"Alice\" --page-size 5 --auth-mode user --format json"
        ),
    )
    user_search.add_argument("--query", required=True, help="Search query")
    user_search.add_argument("--page-size", type=int, help="Page size")
    user_search.add_argument("--page-token", help="Page token")
    user_search.set_defaults(handler=_cmd_contact_user_search)

    department_parser = contact_sub.add_parser("department", help="Department operations")
    department_sub = department_parser.add_subparsers(dest="contact_department_command")
    department_sub.required = True

    department_get = department_sub.add_parser("get", help="Get department by id", parents=[shared])
    department_get.add_argument("--department-id", required=True, help="Department id")
    department_get.add_argument("--user-id-type", help="Optional user_id_type")
    department_get.add_argument("--department-id-type", help="Optional department_id_type")
    department_get.set_defaults(handler=_cmd_contact_department_get)

    department_children = department_sub.add_parser("children", help="List child departments", parents=[shared])
    department_children.add_argument("--department-id", required=True, help="Department id")
    department_children.add_argument("--user-id-type", help="Optional user_id_type")
    department_children.add_argument("--department-id-type", help="Optional department_id_type")
    department_children.add_argument("--fetch-child", choices=("true", "false"), help="Recursive fetch")
    department_children.add_argument("--page-size", type=int, help="Page size")
    department_children.add_argument("--page-token", help="Page token")
    department_children.set_defaults(handler=_cmd_contact_department_children)

    department_batch_get = department_sub.add_parser(
        "batch-get",
        help="Batch get departments by ids",
        parents=[shared],
    )
    department_batch_get.add_argument(
        "--department-id",
        action="append",
        dest="department_ids",
        required=True,
        help="Department id, repeatable",
    )
    department_batch_get.add_argument("--user-id-type", help="Optional user_id_type")
    department_batch_get.add_argument("--department-id-type", help="Optional department_id_type")
    department_batch_get.set_defaults(handler=_cmd_contact_department_batch_get)

    department_parent = department_sub.add_parser("parent", help="List parent departments", parents=[shared])
    department_parent.add_argument("--department-id", required=True, help="Department id")
    department_parent.add_argument("--user-id-type", help="Optional user_id_type")
    department_parent.add_argument("--department-id-type", help="Optional department_id_type")
    department_parent.add_argument("--page-size", type=int, help="Page size")
    department_parent.add_argument("--page-token", help="Page token")
    department_parent.set_defaults(handler=_cmd_contact_department_parent)

    department_search = department_sub.add_parser(
        "search",
        help="Search departments",
        parents=[shared],
    )
    department_search.add_argument("--query", required=True, help="Search query")
    department_search.add_argument("--user-id-type", help="Optional user_id_type")
    department_search.add_argument("--department-id-type", help="Optional department_id_type")
    department_search.add_argument("--page-size", type=int, help="Page size")
    department_search.add_argument("--page-token", help="Page token")
    department_search.set_defaults(handler=_cmd_contact_department_search)

    scope_parser = contact_sub.add_parser("scope", help="Contact scope operations")
    scope_sub = scope_parser.add_subparsers(dest="contact_scope_command")
    scope_sub.required = True

    scope_get = scope_sub.add_parser("get", help="List authorized contact scope", parents=[shared])
    scope_get.add_argument("--user-id-type", help="Optional user_id_type")
    scope_get.add_argument("--department-id-type", help="Optional department_id_type")
    scope_get.add_argument("--page-size", type=int, help="Page size")
    scope_get.add_argument("--page-token", help="Page token")
    scope_get.set_defaults(handler=_cmd_contact_scope_get)
