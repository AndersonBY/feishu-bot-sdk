import json
from typing import Any

from feishu_bot_sdk import cli
from feishu_bot_sdk.task import TaskService


def test_task_help_lists_shortcuts(capsys: Any) -> None:
    code = cli.main(["task", "--help"])
    assert code == 0
    output = capsys.readouterr().out
    assert "+create" in output
    assert "+delete" in output
    assert "+assign" in output
    assert "+get-my-tasks" in output


def test_task_create_shortcut_builds_payload(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    captured: dict[str, Any] = {}

    def _fake_create_task(
        _self: TaskService,
        task: dict[str, Any],
        *,
        user_id_type: str | None = None,
    ) -> dict[str, Any]:
        captured["task"] = task
        captured["user_id_type"] = user_id_type
        return {"task": {"guid": "task_1", "summary": task["summary"], "url": "https://feishu.cn/task_1"}}

    monkeypatch.setattr("feishu_bot_sdk.task.TaskService.create_task", _fake_create_task)

    code = cli.main(
        [
            "task",
            "+create",
            "--summary",
            "Ship feature",
            "--description",
            "Prepare release notes",
            "--assignee",
            "ou_user_1",
            "--due",
            "+2d",
            "--tasklist-id",
            "https://example.com/tasklists/view?guid=tl_1",
            "--idempotency-key",
            "token_1",
            "--format",
            "json",
        ]
    )

    assert code == 0
    assert captured["user_id_type"] == "open_id"
    assert captured["task"]["summary"] == "Ship feature"
    assert captured["task"]["description"] == "Prepare release notes"
    assert captured["task"]["members"] == [{"id": "ou_user_1", "role": "assignee", "type": "user"}]
    assert captured["task"]["tasklists"] == [{"tasklist_guid": "tl_1"}]
    assert captured["task"]["client_token"] == "token_1"
    assert captured["task"]["due"]["is_all_day"] is True
    assert captured["task"]["due"]["timestamp"].isdigit()
    payload = json.loads(capsys.readouterr().out)
    assert payload["guid"] == "task_1"
    assert payload["summary"] == "Ship feature"


def test_task_comment_shortcut(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    captured: dict[str, Any] = {}

    def _fake_create_comment(_self: TaskService, task_guid: str, content: str) -> dict[str, Any]:
        captured["task_guid"] = task_guid
        captured["content"] = content
        return {"comment": {"id": "cmt_1"}}

    monkeypatch.setattr("feishu_bot_sdk.task.TaskService.create_comment", _fake_create_comment)

    code = cli.main(
        [
            "task",
            "+comment",
            "--task-id",
            "task_1",
            "--content",
            "Looks good",
            "--format",
            "json",
        ]
    )

    assert code == 0
    assert captured == {"task_guid": "task_1", "content": "Looks good"}
    payload = json.loads(capsys.readouterr().out)
    assert payload["task_id"] == "task_1"
    assert payload["comment"]["id"] == "cmt_1"


def test_task_delete_shortcut(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    captured: dict[str, Any] = {}

    def _fake_delete_task(_self: TaskService, task_guid: str) -> dict[str, Any]:
        captured["task_guid"] = task_guid
        return {}

    monkeypatch.setattr("feishu_bot_sdk.task.TaskService.delete_task", _fake_delete_task)

    code = cli.main(
        [
            "task",
            "+delete",
            "--task-id",
            "task_1",
            "--format",
            "json",
        ]
    )

    assert code == 0
    assert captured == {"task_guid": "task_1"}
    payload = json.loads(capsys.readouterr().out)
    assert payload["task_id"] == "task_1"
    assert payload["guid"] == "task_1"
    assert payload["deleted"] is True


def test_task_complete_shortcut_skips_when_already_completed(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    monkeypatch.setattr(
        "feishu_bot_sdk.task.TaskService.get_task",
        lambda _self, task_guid, user_id_type=None: {
            "task": {
                "guid": task_guid,
                "summary": "Done already",
                "url": "https://feishu.cn/task_1",
                "completed_at": "1710000000000",
            }
        },
    )
    monkeypatch.setattr(
        "feishu_bot_sdk.task.TaskService.update_task",
        lambda _self, task_guid, task, update_fields=None, user_id_type=None: (_ for _ in ()).throw(
            AssertionError("update_task should not be called for completed task")
        ),
    )

    code = cli.main(
        [
            "task",
            "+complete",
            "--task-id",
            "task_1",
            "--format",
            "json",
        ]
    )

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["guid"] == "task_1"
    assert payload["completed"] is True
    assert payload["changed"] is False


def test_task_assign_and_followers_shortcuts(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    captured: dict[str, Any] = {}

    def _fake_add_members(
        _self: TaskService,
        task_guid: str,
        members: list[dict[str, Any]],
        *,
        client_token: str | None = None,
        user_id_type: str | None = None,
    ) -> dict[str, Any]:
        captured.setdefault("add_calls", []).append(
            {
                "task_guid": task_guid,
                "members": members,
                "client_token": client_token,
                "user_id_type": user_id_type,
            }
        )
        return {"task": {"guid": task_guid, "url": "https://feishu.cn/task_1", "members": members}}

    monkeypatch.setattr("feishu_bot_sdk.task.TaskService.add_task_members", _fake_add_members)

    code = cli.main(
        [
            "task",
            "+assign",
            "--task-id",
            "task_1",
            "--add",
            "ou_a,ou_b",
            "--idempotency-key",
            "token_assign",
            "--format",
            "json",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["member_role"] == "assignee"
    assert payload["member_ids"] == ["ou_a", "ou_b"]
    assert payload["member_count"] == 2

    code = cli.main(
        [
            "task",
            "+followers",
            "--task-id",
            "task_1",
            "--add",
            "ou_f_1",
            "--format",
            "json",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["member_role"] == "follower"
    assert payload["member_ids"] == ["ou_f_1"]
    assert captured["add_calls"][0]["members"] == [
        {"id": "ou_a", "role": "assignee", "type": "user"},
        {"id": "ou_b", "role": "assignee", "type": "user"},
    ]
    assert captured["add_calls"][1]["members"] == [
        {"id": "ou_f_1", "role": "follower", "type": "user"}
    ]


def test_task_reminder_shortcut_replaces_existing_reminders(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    captured: dict[str, Any] = {"get_calls": 0}

    def _fake_get_task(_self: TaskService, task_guid: str, *, user_id_type: str | None = None) -> dict[str, Any]:
        captured["get_calls"] += 1
        if captured["get_calls"] == 1:
            return {
                "task": {
                    "guid": task_guid,
                    "url": "https://feishu.cn/task_1",
                    "reminders": [{"id": "rid_old", "relative_fire_minute": 30}],
                }
            }
        return {
            "task": {
                "guid": task_guid,
                "url": "https://feishu.cn/task_1",
                "reminders": [{"id": "rid_new", "relative_fire_minute": 60}],
            }
        }

    monkeypatch.setattr("feishu_bot_sdk.task.TaskService.get_task", _fake_get_task)
    monkeypatch.setattr(
        "feishu_bot_sdk.task.TaskService.remove_task_reminders",
        lambda _self, task_guid, reminder_ids, user_id_type=None: captured.setdefault(
            "removed", {"task_guid": task_guid, "reminder_ids": reminder_ids, "user_id_type": user_id_type}
        ),
    )
    monkeypatch.setattr(
        "feishu_bot_sdk.task.TaskService.add_task_reminders",
        lambda _self, task_guid, reminders, user_id_type=None: captured.setdefault(
            "added", {"task_guid": task_guid, "reminders": reminders, "user_id_type": user_id_type}
        ),
    )

    code = cli.main(
        [
            "task",
            "+reminder",
            "--task-id",
            "task_1",
            "--set",
            "1h",
            "--format",
            "json",
        ]
    )

    assert code == 0
    assert captured["removed"] == {
        "task_guid": "task_1",
        "reminder_ids": ["rid_old"],
        "user_id_type": "open_id",
    }
    assert captured["added"] == {
        "task_guid": "task_1",
        "reminders": [{"relative_fire_minute": 60}],
        "user_id_type": "open_id",
    }
    payload = json.loads(capsys.readouterr().out)
    assert payload["reminder_count"] == 1
    assert payload["relative_fire_minute"] == 60


def test_task_get_my_tasks_filters_and_paginates(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")
    monkeypatch.setenv("FEISHU_USER_ACCESS_TOKEN", "user_access_token_x")

    captured: list[dict[str, Any]] = []

    def _fake_list_tasks(
        _self: TaskService,
        *,
        type: str | None = None,
        page_size: int | None = None,
        page_token: str | None = None,
        completed: bool | None = None,
        user_id_type: str | None = None,
    ) -> dict[str, Any]:
        captured.append(
            {
                "type": type,
                "page_size": page_size,
                "page_token": page_token,
                "completed": completed,
                "user_id_type": user_id_type,
            }
        )
        if page_token == "p2":
            return {
                "items": [
                    {
                        "guid": "task_3",
                        "summary": "Alpha extension",
                        "created_at": "1767225600000",
                        "due": {"timestamp": "1772323200000"},
                        "url": "https://feishu.cn/task_3",
                    }
                ],
                "has_more": False,
            }
        return {
            "items": [
                {
                    "guid": "task_1",
                    "summary": "Alpha",
                    "created_at": "1764547200000",
                    "due": {"timestamp": "1770076800000"},
                    "url": "https://feishu.cn/task_1",
                },
                {
                    "guid": "task_2",
                    "summary": "Other",
                    "created_at": "1764547200000",
                    "url": "https://feishu.cn/task_2",
                },
            ],
            "has_more": True,
            "page_token": "p2",
        }

    monkeypatch.setattr("feishu_bot_sdk.task.TaskService.list_tasks", _fake_list_tasks)

    code = cli.main(
        [
            "task",
            "+get-my-tasks",
            "--query",
            "Alpha",
            "--created-at",
            "2025-12-01",
            "--due-start",
            "2026-02-01",
            "--page-all",
            "--page-limit",
            "5",
            "--format",
            "json",
        ]
    )

    assert code == 0
    assert captured[0] == {
        "type": "my_tasks",
        "page_size": 50,
        "page_token": None,
        "completed": False,
        "user_id_type": "open_id",
    }
    assert captured[1]["page_token"] == "p2"
    payload = json.loads(capsys.readouterr().out)
    assert payload["count"] == 1
    assert payload["pages"] == 2
    assert payload["items"][0]["guid"] == "task_1"
