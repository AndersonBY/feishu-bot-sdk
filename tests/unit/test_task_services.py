import asyncio
from typing import Any, Mapping, Optional, cast

from feishu_bot_sdk.task import AsyncTaskService, TaskService
from feishu_bot_sdk.feishu import AsyncFeishuClient, FeishuClient


class _SyncClientStub:
    def __init__(self, resolver: Any) -> None:
        self._resolver = resolver
        self.calls: list[dict[str, Any]] = []

    def request_json(
        self,
        method: str,
        path: str,
        *,
        payload: Optional[Mapping[str, object]] = None,
        params: Optional[Mapping[str, object]] = None,
    ) -> Mapping[str, Any]:
        call = {
            "method": method,
            "path": path,
            "payload": dict(payload or {}),
            "params": dict(params or {}),
        }
        self.calls.append(call)
        return self._resolver(call)


class _AsyncClientStub:
    def __init__(self, resolver: Any) -> None:
        self._resolver = resolver
        self.calls: list[dict[str, Any]] = []

    async def request_json(
        self,
        method: str,
        path: str,
        *,
        payload: Optional[Mapping[str, object]] = None,
        params: Optional[Mapping[str, object]] = None,
    ) -> Mapping[str, Any]:
        call = {
            "method": method,
            "path": path,
            "payload": dict(payload or {}),
            "params": dict(params or {}),
        }
        self.calls.append(call)
        return self._resolver(call)


def test_task_crud_requests():
    def resolver(_call: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"code": 0, "data": {"ok": True}}

    stub = _SyncClientStub(resolver)
    service = TaskService(cast(FeishuClient, stub))

    # create_task
    service.create_task({"summary": "Buy milk"}, user_id_type="open_id")
    assert stub.calls[0]["method"] == "POST"
    assert stub.calls[0]["path"] == "/task/v2/tasks"
    assert stub.calls[0]["payload"] == {"summary": "Buy milk"}
    assert stub.calls[0]["params"] == {"user_id_type": "open_id"}

    # get_task
    service.get_task("task_001", user_id_type="open_id")
    assert stub.calls[1]["method"] == "GET"
    assert stub.calls[1]["path"] == "/task/v2/tasks/task_001"
    assert stub.calls[1]["params"] == {"user_id_type": "open_id"}

    # list_tasks
    service.list_tasks(page_size=20, completed=True)
    assert stub.calls[2]["method"] == "GET"
    assert stub.calls[2]["path"] == "/task/v2/tasks"
    assert stub.calls[2]["params"] == {"page_size": 20, "completed": True}

    # update_task
    service.update_task(
        "task_001",
        {"summary": "Buy eggs"},
        update_fields=["summary"],
        user_id_type="open_id",
    )
    assert stub.calls[3]["method"] == "PATCH"
    assert stub.calls[3]["path"] == "/task/v2/tasks/task_001"
    assert stub.calls[3]["payload"] == {"task": {"summary": "Buy eggs"}, "update_fields": ["summary"]}
    assert stub.calls[3]["params"] == {"user_id_type": "open_id"}

    assert len(stub.calls) == 4


def test_iter_tasks_pagination():
    def resolver(call: Mapping[str, Any]) -> Mapping[str, Any]:
        page_token = call["params"].get("page_token")
        if page_token == "p2":
            return {
                "code": 0,
                "data": {"items": [{"guid": "task_2"}], "has_more": False},
            }
        return {
            "code": 0,
            "data": {
                "items": [{"guid": "task_1"}],
                "has_more": True,
                "page_token": "p2",
            },
        }

    stub = _SyncClientStub(resolver)
    service = TaskService(cast(FeishuClient, stub))

    items = list(service.iter_tasks(page_size=1))

    assert items == [{"guid": "task_1"}, {"guid": "task_2"}]
    assert len(stub.calls) == 2
    assert stub.calls[0]["path"] == "/task/v2/tasks"
    assert stub.calls[0]["params"] == {"page_size": 1}
    assert stub.calls[1]["params"] == {"page_size": 1, "page_token": "p2"}


def test_tasklist_crud():
    def resolver(_call: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"code": 0, "data": {"ok": True}}

    stub = _SyncClientStub(resolver)
    service = TaskService(cast(FeishuClient, stub))

    # create_tasklist
    service.create_tasklist({"name": "Sprint 1"}, user_id_type="open_id")
    assert stub.calls[0]["method"] == "POST"
    assert stub.calls[0]["path"] == "/task/v2/tasklists"
    assert stub.calls[0]["payload"] == {"name": "Sprint 1"}
    assert stub.calls[0]["params"] == {"user_id_type": "open_id"}

    # get_tasklist
    service.get_tasklist("tl_001", user_id_type="open_id")
    assert stub.calls[1]["method"] == "GET"
    assert stub.calls[1]["path"] == "/task/v2/tasklists/tl_001"
    assert stub.calls[1]["params"] == {"user_id_type": "open_id"}

    # list_tasklists
    service.list_tasklists(page_size=10)
    assert stub.calls[2]["method"] == "GET"
    assert stub.calls[2]["path"] == "/task/v2/tasklists"
    assert stub.calls[2]["params"] == {"page_size": 10}

    # update_tasklist
    service.update_tasklist(
        "tl_001",
        {"name": "Sprint 2"},
        update_fields=["name"],
        user_id_type="open_id",
    )
    assert stub.calls[3]["method"] == "PATCH"
    assert stub.calls[3]["path"] == "/task/v2/tasklists/tl_001"
    assert stub.calls[3]["payload"] == {"tasklist": {"name": "Sprint 2"}, "update_fields": ["name"]}
    assert stub.calls[3]["params"] == {"user_id_type": "open_id"}

    # delete_tasklist
    service.delete_tasklist("tl_001")
    assert stub.calls[4]["method"] == "DELETE"
    assert stub.calls[4]["path"] == "/task/v2/tasklists/tl_001"
    assert stub.calls[4]["payload"] == {}
    assert stub.calls[4]["params"] == {}

    assert len(stub.calls) == 5


def test_tasklist_members():
    def resolver(_call: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"code": 0, "data": {"ok": True}}

    stub = _SyncClientStub(resolver)
    service = TaskService(cast(FeishuClient, stub))

    members = [{"id": "ou_111", "type": "user", "role": "editor"}]

    # add_tasklist_members
    service.add_tasklist_members("tl_001", members)
    assert stub.calls[0]["method"] == "POST"
    assert stub.calls[0]["path"] == "/task/v2/tasklists/tl_001/members"
    assert stub.calls[0]["payload"] == {"members": [{"id": "ou_111", "type": "user", "role": "editor"}]}

    # remove_tasklist_members
    service.remove_tasklist_members("tl_001", members)
    assert stub.calls[1]["method"] == "POST"
    assert stub.calls[1]["path"] == "/task/v2/tasklists/tl_001/members/batch_delete"
    assert stub.calls[1]["payload"] == {"members": [{"id": "ou_111", "type": "user", "role": "editor"}]}

    assert len(stub.calls) == 2


def test_subtask_crud():
    def resolver(_call: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"code": 0, "data": {"ok": True}}

    stub = _SyncClientStub(resolver)
    service = TaskService(cast(FeishuClient, stub))

    # create_subtask
    service.create_subtask("task_001", {"summary": "Sub 1"}, user_id_type="open_id")
    assert stub.calls[0]["method"] == "POST"
    assert stub.calls[0]["path"] == "/task/v2/tasks/task_001/subtasks"
    assert stub.calls[0]["payload"] == {"summary": "Sub 1"}
    assert stub.calls[0]["params"] == {"user_id_type": "open_id"}

    # list_subtasks
    service.list_subtasks("task_001", page_size=5)
    assert stub.calls[1]["method"] == "GET"
    assert stub.calls[1]["path"] == "/task/v2/tasks/task_001/subtasks"
    assert stub.calls[1]["params"] == {"page_size": 5}

    assert len(stub.calls) == 2


def test_comment_crud():
    def resolver(_call: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"code": 0, "data": {"ok": True}}

    stub = _SyncClientStub(resolver)
    service = TaskService(cast(FeishuClient, stub))

    # create_comment without reply
    service.create_comment("task_001", "Hello")
    assert stub.calls[0]["method"] == "POST"
    assert stub.calls[0]["path"] == "/task/v2/comments"
    assert stub.calls[0]["payload"] == {"content": "Hello", "resource_type": "task", "resource_id": "task_001"}

    # create_comment with reply_to_comment_id
    service.create_comment("task_001", "Reply", reply_to_comment_id="cmt_100")
    assert stub.calls[1]["method"] == "POST"
    assert stub.calls[1]["path"] == "/task/v2/comments"
    assert stub.calls[1]["payload"] == {"content": "Reply", "resource_type": "task", "resource_id": "task_001", "reply_to_comment_id": "cmt_100"}

    # get_comment
    service.get_comment("task_001", "cmt_100")
    assert stub.calls[2]["method"] == "GET"
    assert stub.calls[2]["path"] == "/task/v2/comments/cmt_100"

    # list_comments
    service.list_comments("task_001", page_size=10)
    assert stub.calls[3]["method"] == "GET"
    assert stub.calls[3]["path"] == "/task/v2/comments"
    assert stub.calls[3]["params"] == {"resource_type": "task", "resource_id": "task_001", "page_size": 10}

    assert len(stub.calls) == 4


def test_async_iter_subtasks():
    def resolver(call: Mapping[str, Any]) -> Mapping[str, Any]:
        page_token = call["params"].get("page_token")
        if page_token == "p2":
            return {
                "code": 0,
                "data": {"items": [{"guid": "sub_2"}], "has_more": False},
            }
        return {
            "code": 0,
            "data": {
                "items": [{"guid": "sub_1"}],
                "has_more": True,
                "page_token": "p2",
            },
        }

    stub = _AsyncClientStub(resolver)
    service = AsyncTaskService(cast(AsyncFeishuClient, stub))

    async def run() -> list[Mapping[str, Any]]:
        output: list[Mapping[str, Any]] = []
        async for item in service.iter_subtasks("task_001", page_size=1):
            output.append(item)
        return output

    items = asyncio.run(run())
    assert items == [{"guid": "sub_1"}, {"guid": "sub_2"}]
    assert len(stub.calls) == 2
    assert stub.calls[0]["path"] == "/task/v2/tasks/task_001/subtasks"
    assert stub.calls[0]["params"] == {"page_size": 1}
    assert stub.calls[1]["params"] == {"page_size": 1, "page_token": "p2"}
