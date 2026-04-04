from typing import Any, AsyncIterator, Iterator, Mapping, Optional, Sequence

from .feishu import AsyncFeishuClient, FeishuClient
from .response import DataResponse


def _drop_none(params: Mapping[str, object]) -> dict[str, object]:
    return {key: value for key, value in params.items() if value is not None}


def _unwrap_data(response: Mapping[str, Any]) -> DataResponse:
    return DataResponse.from_raw(response)


def _iter_page_items(data: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
    items = data.get("items")
    if not isinstance(items, list):
        return
    for item in items:
        if isinstance(item, Mapping):
            yield item


def _next_page_token(data: Mapping[str, Any]) -> Optional[str]:
    token = data.get("page_token")
    if isinstance(token, str) and token:
        return token
    return None


def _has_more(data: Mapping[str, Any]) -> bool:
    return bool(data.get("has_more"))


class TaskService:
    def __init__(self, feishu_client: FeishuClient) -> None:
        self._client = feishu_client

    # ── Task CRUD ──

    def create_task(
        self,
        task: Mapping[str, object],
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        response = self._client.request_json(
            "POST",
            "/task/v2/tasks",
            params=params,
            payload=dict(task),
        )
        return _unwrap_data(response)

    def get_task(
        self,
        task_guid: str,
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        response = self._client.request_json(
            "GET",
            f"/task/v2/tasks/{task_guid}",
            params=params,
        )
        return _unwrap_data(response)

    def list_tasks(
        self,
        *,
        type: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        completed: Optional[bool] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "type": type,
                "page_size": page_size,
                "page_token": page_token,
                "completed": completed,
                "user_id_type": user_id_type,
            }
        )
        response = self._client.request_json(
            "GET",
            "/task/v2/tasks",
            params=params,
        )
        return _unwrap_data(response)

    def iter_tasks(
        self,
        *,
        type: Optional[str] = None,
        page_size: int = 50,
        completed: Optional[bool] = None,
        user_id_type: Optional[str] = None,
    ) -> Iterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = self.list_tasks(
                type=type,
                page_size=page_size,
                page_token=page_token,
                completed=completed,
                user_id_type=user_id_type,
            )
            yield from _iter_page_items(data)
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    def update_task(
        self,
        task_guid: str,
        task: Mapping[str, object],
        *,
        update_fields: Optional[list[str]] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        payload: dict[str, object] = {"task": dict(task)}
        if update_fields is not None:
            payload["update_fields"] = list(update_fields)
        response = self._client.request_json(
            "PATCH",
            f"/task/v2/tasks/{task_guid}",
            params=params,
            payload=payload,
        )
        return _unwrap_data(response)

    def delete_task(self, task_guid: str) -> Mapping[str, Any]:
        response = self._client.request_json(
            "DELETE",
            f"/task/v2/tasks/{task_guid}",
        )
        return _unwrap_data(response)

    def add_task_members(
        self,
        task_guid: str,
        members: Sequence[Mapping[str, object]],
        *,
        client_token: Optional[str] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        payload: dict[str, object] = {"members": [dict(member) for member in members]}
        if client_token is not None:
            payload["client_token"] = client_token
        response = self._client.request_json(
            "POST",
            f"/task/v2/tasks/{task_guid}/add_members",
            params=params,
            payload=payload,
        )
        return _unwrap_data(response)

    def remove_task_members(
        self,
        task_guid: str,
        members: Sequence[Mapping[str, object]],
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        response = self._client.request_json(
            "POST",
            f"/task/v2/tasks/{task_guid}/remove_members",
            params=params,
            payload={"members": [dict(member) for member in members]},
        )
        return _unwrap_data(response)

    def add_task_reminders(
        self,
        task_guid: str,
        reminders: list[Mapping[str, object]],
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        response = self._client.request_json(
            "POST",
            f"/task/v2/tasks/{task_guid}/add_reminders",
            params=params,
            payload={"reminders": [dict(reminder) for reminder in reminders]},
        )
        return _unwrap_data(response)

    def remove_task_reminders(
        self,
        task_guid: str,
        reminder_ids: list[str],
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        response = self._client.request_json(
            "POST",
            f"/task/v2/tasks/{task_guid}/remove_reminders",
            params=params,
            payload={"reminder_ids": list(reminder_ids)},
        )
        return _unwrap_data(response)

    # ── TaskList CRUD ──

    def create_tasklist(
        self,
        tasklist: Mapping[str, object],
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        response = self._client.request_json(
            "POST",
            "/task/v2/tasklists",
            params=params,
            payload=dict(tasklist),
        )
        return _unwrap_data(response)

    def get_tasklist(
        self,
        tasklist_guid: str,
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        response = self._client.request_json(
            "GET",
            f"/task/v2/tasklists/{tasklist_guid}",
            params=params,
        )
        return _unwrap_data(response)

    def list_tasklists(
        self,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "page_size": page_size,
                "page_token": page_token,
                "user_id_type": user_id_type,
            }
        )
        response = self._client.request_json(
            "GET",
            "/task/v2/tasklists",
            params=params,
        )
        return _unwrap_data(response)

    def iter_tasklists(
        self,
        *,
        page_size: int = 50,
        user_id_type: Optional[str] = None,
    ) -> Iterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = self.list_tasklists(
                page_size=page_size,
                page_token=page_token,
                user_id_type=user_id_type,
            )
            yield from _iter_page_items(data)
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    def update_tasklist(
        self,
        tasklist_guid: str,
        tasklist: Mapping[str, object],
        *,
        update_fields: Optional[list[str]] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        payload: dict[str, object] = {"tasklist": dict(tasklist)}
        if update_fields is not None:
            payload["update_fields"] = list(update_fields)
        response = self._client.request_json(
            "PATCH",
            f"/task/v2/tasklists/{tasklist_guid}",
            params=params,
            payload=payload,
        )
        return _unwrap_data(response)

    def delete_tasklist(self, tasklist_guid: str) -> Mapping[str, Any]:
        response = self._client.request_json(
            "DELETE",
            f"/task/v2/tasklists/{tasklist_guid}",
        )
        return _unwrap_data(response)

    # ── TaskList Members ──

    def add_tasklist_members(
        self,
        tasklist_guid: str,
        members: list[Mapping[str, object]],
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            f"/task/v2/tasklists/{tasklist_guid}/members",
            payload={"members": [dict(m) for m in members]},
        )
        return _unwrap_data(response)

    def remove_tasklist_members(
        self,
        tasklist_guid: str,
        members: list[Mapping[str, object]],
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            f"/task/v2/tasklists/{tasklist_guid}/members/batch_delete",
            payload={"members": [dict(m) for m in members]},
        )
        return _unwrap_data(response)

    def list_tasklist_tasks(
        self,
        tasklist_guid: str,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        completed: Optional[bool] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "page_size": page_size,
                "page_token": page_token,
                "completed": completed,
                "user_id_type": user_id_type,
            }
        )
        response = self._client.request_json(
            "GET",
            f"/task/v2/tasklists/{tasklist_guid}/tasks",
            params=params,
        )
        return _unwrap_data(response)

    def iter_tasklist_tasks(
        self,
        tasklist_guid: str,
        *,
        page_size: int = 50,
        completed: Optional[bool] = None,
        user_id_type: Optional[str] = None,
    ) -> Iterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = self.list_tasklist_tasks(
                tasklist_guid,
                page_size=page_size,
                page_token=page_token,
                completed=completed,
                user_id_type=user_id_type,
            )
            yield from _iter_page_items(data)
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    # ── Subtask ──

    def create_subtask(
        self,
        task_guid: str,
        subtask: Mapping[str, object],
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        response = self._client.request_json(
            "POST",
            f"/task/v2/tasks/{task_guid}/subtasks",
            params=params,
            payload=dict(subtask),
        )
        return _unwrap_data(response)

    def list_subtasks(
        self,
        task_guid: str,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "page_size": page_size,
                "page_token": page_token,
                "user_id_type": user_id_type,
            }
        )
        response = self._client.request_json(
            "GET",
            f"/task/v2/tasks/{task_guid}/subtasks",
            params=params,
        )
        return _unwrap_data(response)

    def iter_subtasks(
        self,
        task_guid: str,
        *,
        page_size: int = 50,
        user_id_type: Optional[str] = None,
    ) -> Iterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = self.list_subtasks(
                task_guid,
                page_size=page_size,
                page_token=page_token,
                user_id_type=user_id_type,
            )
            yield from _iter_page_items(data)
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    # ── Comment ──

    def create_comment(
        self,
        task_guid: str,
        content: str,
        *,
        reply_to_comment_id: Optional[str] = None,
    ) -> Mapping[str, Any]:
        payload: dict[str, object] = {
            "content": content,
            "resource_type": "task",
            "resource_id": task_guid,
        }
        if reply_to_comment_id is not None:
            payload["reply_to_comment_id"] = reply_to_comment_id
        response = self._client.request_json(
            "POST",
            "/task/v2/comments",
            payload=payload,
        )
        return _unwrap_data(response)

    def get_comment(
        self,
        task_guid: str,
        comment_id: str,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "GET",
            f"/task/v2/comments/{comment_id}",
        )
        return _unwrap_data(response)

    def list_comments(
        self,
        task_guid: str,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "resource_type": "task",
                "resource_id": task_guid,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        response = self._client.request_json(
            "GET",
            "/task/v2/comments",
            params=params,
        )
        return _unwrap_data(response)

    def iter_comments(
        self,
        task_guid: str,
        *,
        page_size: int = 50,
    ) -> Iterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = self.list_comments(
                task_guid,
                page_size=page_size,
                page_token=page_token,
            )
            yield from _iter_page_items(data)
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return


class AsyncTaskService:
    def __init__(self, feishu_client: AsyncFeishuClient) -> None:
        self._client = feishu_client

    # ── Task CRUD ──

    async def create_task(
        self,
        task: Mapping[str, object],
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        response = await self._client.request_json(
            "POST",
            "/task/v2/tasks",
            params=params,
            payload=dict(task),
        )
        return _unwrap_data(response)

    async def get_task(
        self,
        task_guid: str,
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        response = await self._client.request_json(
            "GET",
            f"/task/v2/tasks/{task_guid}",
            params=params,
        )
        return _unwrap_data(response)

    async def list_tasks(
        self,
        *,
        type: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        completed: Optional[bool] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "type": type,
                "page_size": page_size,
                "page_token": page_token,
                "completed": completed,
                "user_id_type": user_id_type,
            }
        )
        response = await self._client.request_json(
            "GET",
            "/task/v2/tasks",
            params=params,
        )
        return _unwrap_data(response)

    async def iter_tasks(
        self,
        *,
        type: Optional[str] = None,
        page_size: int = 50,
        completed: Optional[bool] = None,
        user_id_type: Optional[str] = None,
    ) -> AsyncIterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = await self.list_tasks(
                type=type,
                page_size=page_size,
                page_token=page_token,
                completed=completed,
                user_id_type=user_id_type,
            )
            for item in _iter_page_items(data):
                yield item
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    async def update_task(
        self,
        task_guid: str,
        task: Mapping[str, object],
        *,
        update_fields: Optional[list[str]] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        payload: dict[str, object] = {"task": dict(task)}
        if update_fields is not None:
            payload["update_fields"] = list(update_fields)
        response = await self._client.request_json(
            "PATCH",
            f"/task/v2/tasks/{task_guid}",
            params=params,
            payload=payload,
        )
        return _unwrap_data(response)

    async def delete_task(self, task_guid: str) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "DELETE",
            f"/task/v2/tasks/{task_guid}",
        )
        return _unwrap_data(response)

    async def add_task_members(
        self,
        task_guid: str,
        members: Sequence[Mapping[str, object]],
        *,
        client_token: Optional[str] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        payload: dict[str, object] = {"members": [dict(member) for member in members]}
        if client_token is not None:
            payload["client_token"] = client_token
        response = await self._client.request_json(
            "POST",
            f"/task/v2/tasks/{task_guid}/add_members",
            params=params,
            payload=payload,
        )
        return _unwrap_data(response)

    async def remove_task_members(
        self,
        task_guid: str,
        members: Sequence[Mapping[str, object]],
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        response = await self._client.request_json(
            "POST",
            f"/task/v2/tasks/{task_guid}/remove_members",
            params=params,
            payload={"members": [dict(member) for member in members]},
        )
        return _unwrap_data(response)

    async def add_task_reminders(
        self,
        task_guid: str,
        reminders: list[Mapping[str, object]],
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        response = await self._client.request_json(
            "POST",
            f"/task/v2/tasks/{task_guid}/add_reminders",
            params=params,
            payload={"reminders": [dict(reminder) for reminder in reminders]},
        )
        return _unwrap_data(response)

    async def remove_task_reminders(
        self,
        task_guid: str,
        reminder_ids: list[str],
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        response = await self._client.request_json(
            "POST",
            f"/task/v2/tasks/{task_guid}/remove_reminders",
            params=params,
            payload={"reminder_ids": list(reminder_ids)},
        )
        return _unwrap_data(response)

    # ── TaskList CRUD ──

    async def create_tasklist(
        self,
        tasklist: Mapping[str, object],
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        response = await self._client.request_json(
            "POST",
            "/task/v2/tasklists",
            params=params,
            payload=dict(tasklist),
        )
        return _unwrap_data(response)

    async def get_tasklist(
        self,
        tasklist_guid: str,
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        response = await self._client.request_json(
            "GET",
            f"/task/v2/tasklists/{tasklist_guid}",
            params=params,
        )
        return _unwrap_data(response)

    async def list_tasklists(
        self,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "page_size": page_size,
                "page_token": page_token,
                "user_id_type": user_id_type,
            }
        )
        response = await self._client.request_json(
            "GET",
            "/task/v2/tasklists",
            params=params,
        )
        return _unwrap_data(response)

    async def iter_tasklists(
        self,
        *,
        page_size: int = 50,
        user_id_type: Optional[str] = None,
    ) -> AsyncIterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = await self.list_tasklists(
                page_size=page_size,
                page_token=page_token,
                user_id_type=user_id_type,
            )
            for item in _iter_page_items(data):
                yield item
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    async def update_tasklist(
        self,
        tasklist_guid: str,
        tasklist: Mapping[str, object],
        *,
        update_fields: Optional[list[str]] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        payload: dict[str, object] = {"tasklist": dict(tasklist)}
        if update_fields is not None:
            payload["update_fields"] = list(update_fields)
        response = await self._client.request_json(
            "PATCH",
            f"/task/v2/tasklists/{tasklist_guid}",
            params=params,
            payload=payload,
        )
        return _unwrap_data(response)

    async def delete_tasklist(self, tasklist_guid: str) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "DELETE",
            f"/task/v2/tasklists/{tasklist_guid}",
        )
        return _unwrap_data(response)

    # ── TaskList Members ──

    async def add_tasklist_members(
        self,
        tasklist_guid: str,
        members: list[Mapping[str, object]],
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/task/v2/tasklists/{tasklist_guid}/members",
            payload={"members": [dict(m) for m in members]},
        )
        return _unwrap_data(response)

    async def remove_tasklist_members(
        self,
        tasklist_guid: str,
        members: list[Mapping[str, object]],
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/task/v2/tasklists/{tasklist_guid}/members/batch_delete",
            payload={"members": [dict(m) for m in members]},
        )
        return _unwrap_data(response)

    async def list_tasklist_tasks(
        self,
        tasklist_guid: str,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        completed: Optional[bool] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "page_size": page_size,
                "page_token": page_token,
                "completed": completed,
                "user_id_type": user_id_type,
            }
        )
        response = await self._client.request_json(
            "GET",
            f"/task/v2/tasklists/{tasklist_guid}/tasks",
            params=params,
        )
        return _unwrap_data(response)

    async def iter_tasklist_tasks(
        self,
        tasklist_guid: str,
        *,
        page_size: int = 50,
        completed: Optional[bool] = None,
        user_id_type: Optional[str] = None,
    ) -> AsyncIterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = await self.list_tasklist_tasks(
                tasklist_guid,
                page_size=page_size,
                page_token=page_token,
                completed=completed,
                user_id_type=user_id_type,
            )
            for item in _iter_page_items(data):
                yield item
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    # ── Subtask ──

    async def create_subtask(
        self,
        task_guid: str,
        subtask: Mapping[str, object],
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        response = await self._client.request_json(
            "POST",
            f"/task/v2/tasks/{task_guid}/subtasks",
            params=params,
            payload=dict(subtask),
        )
        return _unwrap_data(response)

    async def list_subtasks(
        self,
        task_guid: str,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "page_size": page_size,
                "page_token": page_token,
                "user_id_type": user_id_type,
            }
        )
        response = await self._client.request_json(
            "GET",
            f"/task/v2/tasks/{task_guid}/subtasks",
            params=params,
        )
        return _unwrap_data(response)

    async def iter_subtasks(
        self,
        task_guid: str,
        *,
        page_size: int = 50,
        user_id_type: Optional[str] = None,
    ) -> AsyncIterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = await self.list_subtasks(
                task_guid,
                page_size=page_size,
                page_token=page_token,
                user_id_type=user_id_type,
            )
            for item in _iter_page_items(data):
                yield item
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    # ── Comment ──

    async def create_comment(
        self,
        task_guid: str,
        content: str,
        *,
        reply_to_comment_id: Optional[str] = None,
    ) -> Mapping[str, Any]:
        payload: dict[str, object] = {
            "content": content,
            "resource_type": "task",
            "resource_id": task_guid,
        }
        if reply_to_comment_id is not None:
            payload["reply_to_comment_id"] = reply_to_comment_id
        response = await self._client.request_json(
            "POST",
            "/task/v2/comments",
            payload=payload,
        )
        return _unwrap_data(response)

    async def get_comment(
        self,
        task_guid: str,
        comment_id: str,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "GET",
            f"/task/v2/comments/{comment_id}",
        )
        return _unwrap_data(response)

    async def list_comments(
        self,
        task_guid: str,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "resource_type": "task",
                "resource_id": task_guid,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        response = await self._client.request_json(
            "GET",
            "/task/v2/comments",
            params=params,
        )
        return _unwrap_data(response)

    async def iter_comments(
        self,
        task_guid: str,
        *,
        page_size: int = 50,
    ) -> AsyncIterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = await self.list_comments(
                task_guid,
                page_size=page_size,
                page_token=page_token,
            )
            for item in _iter_page_items(data):
                yield item
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return
