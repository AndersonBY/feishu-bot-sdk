from __future__ import annotations

import argparse
import json
from typing import Any, Callable, Mapping

from ...task import TaskService
from ..runtime import _build_client, _parse_json_array, _parse_json_object


def _next_page_token(data: Mapping[str, Any]) -> str | None:
    token = data.get("page_token")
    if isinstance(token, str) and token:
        return token
    return None


def _has_more(data: Mapping[str, Any]) -> bool:
    return bool(data.get("has_more"))


def _collect_all_pages(
    fetch_page: Callable[..., Mapping[str, Any]],
    *,
    page_size: int | None,
    page_token: str | None,
    default_page_size: int,
) -> Mapping[str, Any]:
    collected: list[Any] = []
    current_token = page_token
    while True:
        data = fetch_page(page_size=page_size, page_token=current_token)
        items = data.get("items")
        if isinstance(items, list):
            collected.extend(items)
        if not _has_more(data):
            break
        current_token = _next_page_token(data)
        if not current_token:
            break
    return {"all": True, "has_more": False, "count": len(collected), "items": collected}


def _cmd_task_create(args: argparse.Namespace) -> Mapping[str, Any]:
    task: dict[str, object] = {"summary": str(args.summary)}
    description = getattr(args, "description", None)
    if description:
        task["description"] = str(description)
    due = getattr(args, "due", None)
    if due:
        task["due"] = json.loads(str(due))
    members = _parse_json_array(
        json_text=getattr(args, "members_json", None),
        file_path=getattr(args, "members_file", None),
        stdin_enabled=bool(getattr(args, "members_stdin", False)),
        name="members",
        required=False,
    )
    if members:
        task["members"] = members
    service = TaskService(_build_client(args))
    return service.create_task(task)


def _cmd_task_get(args: argparse.Namespace) -> Mapping[str, Any]:
    service = TaskService(_build_client(args))
    return service.get_task(
        str(args.task_guid),
        user_id_type=getattr(args, "user_id_type", None),
    )


def _cmd_task_list(args: argparse.Namespace) -> Mapping[str, Any]:
    service = TaskService(_build_client(args))
    completed = True if bool(getattr(args, "completed", False)) else None
    page_size = getattr(args, "page_size", None)
    page_token = getattr(args, "page_token", None)
    if not bool(getattr(args, "all", False)):
        return service.list_tasks(
            page_size=page_size,
            page_token=page_token,
            completed=completed,
        )
    return _collect_all_pages(
        lambda *, page_size, page_token: service.list_tasks(
            page_size=page_size,
            page_token=page_token,
            completed=completed,
        ),
        page_size=page_size,
        page_token=page_token,
        default_page_size=50,
    )


def _cmd_task_update(args: argparse.Namespace) -> Mapping[str, Any]:
    task = _parse_json_object(
        json_text=getattr(args, "task_json", None),
        file_path=getattr(args, "task_file", None),
        stdin_enabled=bool(getattr(args, "task_stdin", False)),
        name="task",
        required=True,
    )
    raw_fields = getattr(args, "update_fields", None)
    fields_list = [f.strip() for f in raw_fields.split(",") if f.strip()] if raw_fields else None
    service = TaskService(_build_client(args))
    return service.update_task(
        str(args.task_guid),
        task,
        update_fields=fields_list,
    )


def _cmd_task_create_list(args: argparse.Namespace) -> Mapping[str, Any]:
    service = TaskService(_build_client(args))
    return service.create_tasklist({"name": str(args.name)})


def _cmd_task_list_lists(args: argparse.Namespace) -> Mapping[str, Any]:
    service = TaskService(_build_client(args))
    page_size = getattr(args, "page_size", None)
    page_token = getattr(args, "page_token", None)
    if not bool(getattr(args, "all", False)):
        return service.list_tasklists(page_size=page_size, page_token=page_token)
    return _collect_all_pages(
        lambda *, page_size, page_token: service.list_tasklists(
            page_size=page_size,
            page_token=page_token,
        ),
        page_size=page_size,
        page_token=page_token,
        default_page_size=50,
    )


def _cmd_task_create_subtask(args: argparse.Namespace) -> Mapping[str, Any]:
    subtask: dict[str, object] = {"summary": str(args.summary)}
    description = getattr(args, "description", None)
    if description:
        subtask["description"] = str(description)
    service = TaskService(_build_client(args))
    return service.create_subtask(str(args.task_guid), subtask)


def _cmd_task_list_subtasks(args: argparse.Namespace) -> Mapping[str, Any]:
    service = TaskService(_build_client(args))
    page_size = getattr(args, "page_size", None)
    page_token = getattr(args, "page_token", None)
    if not bool(getattr(args, "all", False)):
        return service.list_subtasks(
            str(args.task_guid),
            page_size=page_size,
            page_token=page_token,
        )
    return _collect_all_pages(
        lambda *, page_size, page_token: service.list_subtasks(
            str(args.task_guid),
            page_size=page_size,
            page_token=page_token,
        ),
        page_size=page_size,
        page_token=page_token,
        default_page_size=50,
    )


def _cmd_task_create_comment(args: argparse.Namespace) -> Mapping[str, Any]:
    service = TaskService(_build_client(args))
    return service.create_comment(
        str(args.task_guid),
        str(args.content),
        reply_to_comment_id=getattr(args, "reply_to_comment_id", None),
    )


def _cmd_task_list_comments(args: argparse.Namespace) -> Mapping[str, Any]:
    service = TaskService(_build_client(args))
    page_size = getattr(args, "page_size", None)
    page_token = getattr(args, "page_token", None)
    if not bool(getattr(args, "all", False)):
        return service.list_comments(
            str(args.task_guid),
            page_size=page_size,
            page_token=page_token,
        )
    return _collect_all_pages(
        lambda *, page_size, page_token: service.list_comments(
            str(args.task_guid),
            page_size=page_size,
            page_token=page_token,
        ),
        page_size=page_size,
        page_token=page_token,
        default_page_size=50,
    )


__all__ = [name for name in globals() if name.startswith("_cmd_")]
