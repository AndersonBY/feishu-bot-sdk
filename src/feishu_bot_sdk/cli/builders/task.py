from __future__ import annotations

import argparse

from ..commands.task import (
    _cmd_task_create,
    _cmd_task_create_comment,
    _cmd_task_create_list,
    _cmd_task_create_subtask,
    _cmd_task_get,
    _cmd_task_list,
    _cmd_task_list_comments,
    _cmd_task_list_lists,
    _cmd_task_list_subtasks,
    _cmd_task_update,
)
from ..settings import HELP_FORMATTER as _HELP_FORMATTER


def _build_task_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    shared: argparse.ArgumentParser,
) -> None:
    task_parser = subparsers.add_parser(
        "task",
        help="Task operations (Feishu Task v2)",
        description=(
            "Task operations for creating/listing/updating tasks, tasklists, subtasks, and comments.\n"
            "Supports JSON from --*-json/--*-file/--*-stdin and auto pagination via --all."
        ),
        formatter_class=_HELP_FORMATTER,
        epilog=(
            "Examples:\n"
            '  feishu task create --summary "Review PR" --format json\n'
            "  feishu task list --all --format json\n"
            "  feishu task get --task-guid 6948xxxxx --format json\n"
            '  feishu task create-list --name "Sprint 42" --format json\n'
            '  feishu task create-subtask --task-guid 6948xxxxx --summary "Sub item" --format json'
        ),
    )
    task_sub = task_parser.add_subparsers(dest="task_command")
    task_sub.required = True

    # --- Task CRUD ---
    create = task_sub.add_parser(
        "create",
        help="Create a task",
        parents=[shared],
        description="Create a new task. Returns: task with 'guid'",
        formatter_class=_HELP_FORMATTER,
    )
    create.add_argument("--summary", required=True, help="Task summary/title")
    create.add_argument("--description", help="Optional task description")
    create.add_argument("--due", help='Due date JSON, e.g. {"timestamp":"1704067200","is_all_day":false}')
    create.add_argument("--members-json", help='Members JSON array, e.g. [{"id":"ou_xxx","type":"user","role":"assignee"}]')
    create.add_argument("--members-file", help="Members JSON file path")
    create.add_argument("--members-stdin", action="store_true", help="Read members JSON from stdin")
    create.set_defaults(handler=_cmd_task_create)

    get = task_sub.add_parser("get", help="Get a task by guid", parents=[shared])
    get.add_argument("--task-guid", required=True, help="Task GUID")
    get.add_argument("--user-id-type", help="Optional user_id_type")
    get.set_defaults(handler=_cmd_task_get)

    list_tasks = task_sub.add_parser("list", help="List tasks", parents=[shared])
    list_tasks.add_argument("--completed", action="store_true", help="Include completed tasks")
    list_tasks.add_argument("--page-size", type=int, help="Page size")
    list_tasks.add_argument("--page-token", help="Page token")
    list_tasks.add_argument("--all", action="store_true", help="Auto paginate and return all items")
    list_tasks.set_defaults(handler=_cmd_task_list)

    update = task_sub.add_parser("update", help="Update a task", parents=[shared])
    update.add_argument("--task-guid", required=True, help="Task GUID")
    update.add_argument("--update-fields", help="Comma-separated fields to update, e.g. summary,due,description,completed_at,extra")
    update.add_argument("--task-json", help='Task JSON, e.g. {"summary":"New title","due":{"timestamp":"1704067200"}}')
    update.add_argument("--task-file", help="Task JSON file path")
    update.add_argument("--task-stdin", action="store_true", help="Read task JSON from stdin")
    update.set_defaults(handler=_cmd_task_update)

    # --- TaskList CRUD ---
    create_list = task_sub.add_parser(
        "create-list",
        help="Create a tasklist",
        parents=[shared],
        description="Create a new tasklist. Returns: tasklist with 'guid'",
        formatter_class=_HELP_FORMATTER,
    )
    create_list.add_argument("--name", required=True, help="Tasklist name")
    create_list.set_defaults(handler=_cmd_task_create_list)

    list_lists = task_sub.add_parser("list-lists", help="List tasklists", parents=[shared])
    list_lists.add_argument("--page-size", type=int, help="Page size")
    list_lists.add_argument("--page-token", help="Page token")
    list_lists.add_argument("--all", action="store_true", help="Auto paginate and return all items")
    list_lists.set_defaults(handler=_cmd_task_list_lists)

    # --- Subtask ---
    create_subtask = task_sub.add_parser(
        "create-subtask",
        help="Create a subtask",
        parents=[shared],
        description="Create a subtask under a parent task. Returns: subtask with 'guid'",
        formatter_class=_HELP_FORMATTER,
    )
    create_subtask.add_argument("--task-guid", required=True, help="Parent task GUID")
    create_subtask.add_argument("--summary", required=True, help="Subtask summary/title")
    create_subtask.add_argument("--description", help="Optional subtask description")
    create_subtask.set_defaults(handler=_cmd_task_create_subtask)

    list_subtasks = task_sub.add_parser("list-subtasks", help="List subtasks", parents=[shared])
    list_subtasks.add_argument("--task-guid", required=True, help="Parent task GUID")
    list_subtasks.add_argument("--page-size", type=int, help="Page size")
    list_subtasks.add_argument("--page-token", help="Page token")
    list_subtasks.add_argument("--all", action="store_true", help="Auto paginate and return all items")
    list_subtasks.set_defaults(handler=_cmd_task_list_subtasks)

    # --- Comment ---
    create_comment = task_sub.add_parser(
        "create-comment",
        help="Create a comment",
        parents=[shared],
        description="Create a comment on a task. Returns: comment with 'comment_id'",
        formatter_class=_HELP_FORMATTER,
    )
    create_comment.add_argument("--task-guid", required=True, help="Task GUID")
    create_comment.add_argument("--content", required=True, help="Comment content text")
    create_comment.add_argument("--reply-to-comment-id", help="Optional comment ID to reply to")
    create_comment.set_defaults(handler=_cmd_task_create_comment)

    list_comments = task_sub.add_parser("list-comments", help="List comments", parents=[shared])
    list_comments.add_argument("--task-guid", required=True, help="Task GUID")
    list_comments.add_argument("--page-size", type=int, help="Page size")
    list_comments.add_argument("--page-token", help="Page token")
    list_comments.add_argument("--all", action="store_true", help="Auto paginate and return all items")
    list_comments.set_defaults(handler=_cmd_task_list_comments)
