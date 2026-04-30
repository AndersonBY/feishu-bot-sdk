from __future__ import annotations

from typing import Any

import feishu_bot_sdk.cli as cli
from feishu_bot_sdk.feishu import FeishuClient


def test_task_help_lists_p5_lark_shortcuts(capsys: Any) -> None:
    code = cli.main(["task", "--help"])

    assert code == 0
    output = capsys.readouterr().out
    for command in (
        "+update",
        "+set-ancestor",
        "+get-related-tasks",
        "+search",
        "+subscribe-event",
        "+tasklist-create",
        "+tasklist-search",
        "+tasklist-task-add",
        "+tasklist-members",
    ):
        assert command in output


def test_task_update_search_and_tasklist_flows(monkeypatch: Any, capsys: Any) -> None:
    calls: list[dict[str, Any]] = []

    def _fake_request_json(
        _self: FeishuClient,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        calls.append({"method": method, "path": path, "payload": payload, "params": params})
        if path == "/task/v2/tasks/search":
            return {"code": 0, "data": {"items": [{"id": "task_1"}], "has_more": False}}
        if path == "/task/v2/tasklists":
            return {"code": 0, "data": {"tasklist": {"guid": "tl_1", "name": "Sprint"}}}
        if path == "/task/v2/tasklists/tl_1/members":
            return {"code": 0, "data": {"members": [{"id": "ou_editor"}]}}
        if path == "/task/v2/tasks/task_1/add_tasklist":
            return {"code": 0, "data": {"task": {"guid": "task_1", "url": "https://example.com/task_1"}}}
        return {"code": 0, "data": {"task": {"guid": path.rsplit('/', 1)[-1], "summary": "Updated"}}}

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)
    base = ["--as", "user", "--user-access-token", "user_token", "--format", "json"]

    assert cli.main(["task", "+update", *base, "--task-id", "task_1,task_2", "--summary", "Updated", "--description", "Notes"]) == 0
    capsys.readouterr()
    assert cli.main(["task", "+search", *base, "--query", "roadmap", "--creator", "ou_creator", "--assignee", "ou_assignee", "--completed"]) == 0
    capsys.readouterr()
    assert cli.main(["task", "+tasklist-create", *base, "--name", "Sprint", "--member", "ou_editor", "--data", '[{"summary":"Task A","assignee":"ou_a"}]']) == 0
    capsys.readouterr()
    assert cli.main(["task", "+tasklist-task-add", *base, "--tasklist-id", "https://example.com/tasklists/view?guid=tl_1", "--task-id", "task_1", "--section-guid", "sec_1"]) == 0
    capsys.readouterr()
    assert cli.main(["task", "+tasklist-members", *base, "--tasklist-id", "tl_1", "--add", "ou_editor"]) == 0

    assert calls[0] == {
        "method": "PATCH",
        "path": "/task/v2/tasks/task_1",
        "payload": {"task": {"summary": "Updated", "description": "Notes"}, "update_fields": ["summary", "description"]},
        "params": {"user_id_type": "open_id"},
    }
    assert calls[1]["path"] == "/task/v2/tasks/task_2"
    assert calls[2]["path"] == "/task/v2/tasks/search"
    assert calls[2]["payload"]["query"] == "roadmap"
    assert calls[2]["payload"]["filter"] == {
        "creator_ids": ["ou_creator"],
        "assignee_ids": ["ou_assignee"],
        "is_completed": True,
    }
    assert calls[3]["path"] == "/task/v2/tasklists"
    assert calls[3]["payload"]["members"] == [{"id": "ou_editor", "role": "editor", "type": "user"}]
    assert calls[4]["path"] == "/task/v2/tasks"
    assert calls[4]["payload"]["tasklists"] == [{"tasklist_guid": "tl_1"}]
    assert calls[4]["payload"]["members"] == [{"id": "ou_a", "role": "assignee", "type": "user"}]
    assert calls[5]["path"] == "/task/v2/tasks/task_1/add_tasklist"
    assert calls[5]["payload"] == {"tasklist_guid": "tl_1", "section_guid": "sec_1"}
    assert calls[6]["path"] == "/task/v2/tasklists/tl_1/members"
