from typing import Any, AsyncIterator, Iterator, Mapping, Optional

from .feishu import AsyncFeishuClient, FeishuClient
from .response import DataResponse


def _drop_none(params: Mapping[str, object]) -> dict[str, object]:
    return {key: value for key, value in params.items() if value is not None}


def _unwrap_data(response: Mapping[str, Any]) -> DataResponse:
    return DataResponse.from_raw(response)


def _iter_page_items(data: Mapping[str, Any], key: str = "items") -> Iterator[Mapping[str, Any]]:
    items = data.get(key)
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


class WikiService:
    def __init__(self, feishu_client: FeishuClient) -> None:
        self._client = feishu_client

    def create_space(self, space: Mapping[str, object]) -> Mapping[str, Any]:
        response = self._client.request_json("POST", "/wiki/v2/spaces", payload=dict(space))
        return _unwrap_data(response)

    def list_spaces(
        self,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"page_size": page_size, "page_token": page_token})
        response = self._client.request_json("GET", "/wiki/v2/spaces", params=params)
        return _unwrap_data(response)

    def iter_spaces(self, *, page_size: int = 20) -> Iterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = self.list_spaces(page_size=page_size, page_token=page_token)
            yield from _iter_page_items(data)
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    def get_space(self, space_id: str, *, lang: Optional[str] = None) -> Mapping[str, Any]:
        params = _drop_none({"lang": lang})
        response = self._client.request_json("GET", f"/wiki/v2/spaces/{space_id}", params=params)
        return _unwrap_data(response)

    def get_node(self, token: str, *, obj_type: Optional[str] = None) -> Mapping[str, Any]:
        params = _drop_none({"token": token, "obj_type": obj_type})
        response = self._client.request_json("GET", "/wiki/v2/spaces/get_node", params=params)
        return _unwrap_data(response)

    def search_nodes(
        self,
        query: str,
        *,
        space_id: Optional[str] = None,
        node_id: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"page_size": page_size, "page_token": page_token})
        payload = _drop_none({"query": query, "space_id": space_id, "node_id": node_id})
        response = self._client.request_json(
            "POST",
            "/wiki/v2/nodes/search",
            params=params,
            payload=payload,
        )
        return _unwrap_data(response)

    def iter_search_nodes(
        self,
        query: str,
        *,
        space_id: Optional[str] = None,
        node_id: Optional[str] = None,
        page_size: int = 20,
    ) -> Iterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = self.search_nodes(
                query,
                space_id=space_id,
                node_id=node_id,
                page_size=page_size,
                page_token=page_token,
            )
            yield from _iter_page_items(data)
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    def create_node(self, space_id: str, node: Mapping[str, object]) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            f"/wiki/v2/spaces/{space_id}/nodes",
            payload=dict(node),
        )
        return _unwrap_data(response)

    def list_nodes(
        self,
        space_id: str,
        *,
        parent_node_token: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "parent_node_token": parent_node_token,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        response = self._client.request_json("GET", f"/wiki/v2/spaces/{space_id}/nodes", params=params)
        return _unwrap_data(response)

    def iter_nodes(
        self,
        space_id: str,
        *,
        parent_node_token: Optional[str] = None,
        page_size: int = 50,
    ) -> Iterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = self.list_nodes(
                space_id,
                parent_node_token=parent_node_token,
                page_size=page_size,
                page_token=page_token,
            )
            yield from _iter_page_items(data)
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    def copy_node(
        self,
        space_id: str,
        node_token: str,
        *,
        target_parent_token: Optional[str] = None,
        target_space_id: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Mapping[str, Any]:
        payload = _drop_none(
            {
                "target_parent_token": target_parent_token,
                "target_space_id": target_space_id,
                "title": title,
            }
        )
        response = self._client.request_json(
            "POST",
            f"/wiki/v2/spaces/{space_id}/nodes/{node_token}/copy",
            payload=payload,
        )
        return _unwrap_data(response)

    def move_node(
        self,
        space_id: str,
        node_token: str,
        *,
        target_parent_token: Optional[str] = None,
        target_space_id: Optional[str] = None,
    ) -> Mapping[str, Any]:
        payload = _drop_none(
            {
                "target_parent_token": target_parent_token,
                "target_space_id": target_space_id,
            }
        )
        response = self._client.request_json(
            "POST",
            f"/wiki/v2/spaces/{space_id}/nodes/{node_token}/move",
            payload=payload,
        )
        return _unwrap_data(response)

    def update_node_title(self, space_id: str, node_token: str, *, title: str) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            f"/wiki/v2/spaces/{space_id}/nodes/{node_token}/update_title",
            payload={"title": title},
        )
        return _unwrap_data(response)

    def move_docs_to_wiki(
        self,
        space_id: str,
        *,
        obj_type: str,
        obj_token: str,
        parent_wiki_token: Optional[str] = None,
        apply: Optional[bool] = None,
    ) -> Mapping[str, Any]:
        payload = _drop_none(
            {
                "parent_wiki_token": parent_wiki_token,
                "obj_type": obj_type,
                "obj_token": obj_token,
                "apply": apply,
            }
        )
        response = self._client.request_json(
            "POST",
            f"/wiki/v2/spaces/{space_id}/nodes/move_docs_to_wiki",
            payload=payload,
        )
        return _unwrap_data(response)

    def get_task(self, task_id: str, *, task_type: str) -> Mapping[str, Any]:
        params = _drop_none({"task_type": task_type})
        response = self._client.request_json("GET", f"/wiki/v2/tasks/{task_id}", params=params)
        return _unwrap_data(response)

    def list_members(
        self,
        space_id: str,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"page_size": page_size, "page_token": page_token})
        response = self._client.request_json(
            "GET",
            f"/wiki/v2/spaces/{space_id}/members",
            params=params,
        )
        return _unwrap_data(response)

    def iter_members(self, space_id: str, *, page_size: int = 50) -> Iterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = self.list_members(space_id, page_size=page_size, page_token=page_token)
            yield from _iter_page_items(data, key="members")
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    def add_member(
        self,
        space_id: str,
        *,
        member_type: str,
        member_id: str,
        member_role: str,
        collaborator_type: Optional[str] = None,
        need_notification: Optional[bool] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"need_notification": need_notification})
        payload = _drop_none(
            {
                "member_type": member_type,
                "member_id": member_id,
                "member_role": member_role,
                "type": collaborator_type,
            }
        )
        response = self._client.request_json(
            "POST",
            f"/wiki/v2/spaces/{space_id}/members",
            params=params,
            payload=payload,
        )
        return _unwrap_data(response)

    def remove_member(
        self,
        space_id: str,
        member_id: str,
        *,
        member_type: str,
        member_role: str,
        collaborator_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        payload = _drop_none(
            {
                "member_type": member_type,
                "member_role": member_role,
                "type": collaborator_type,
            }
        )
        response = self._client.request_json(
            "DELETE",
            f"/wiki/v2/spaces/{space_id}/members/{member_id}",
            payload=payload,
        )
        return _unwrap_data(response)

    def update_space_setting(self, space_id: str, setting: Mapping[str, object]) -> Mapping[str, Any]:
        response = self._client.request_json(
            "PUT",
            f"/wiki/v2/spaces/{space_id}/setting",
            payload=dict(setting),
        )
        return _unwrap_data(response)


class AsyncWikiService:
    def __init__(self, feishu_client: AsyncFeishuClient) -> None:
        self._client = feishu_client

    async def create_space(self, space: Mapping[str, object]) -> Mapping[str, Any]:
        response = await self._client.request_json("POST", "/wiki/v2/spaces", payload=dict(space))
        return _unwrap_data(response)

    async def list_spaces(
        self,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"page_size": page_size, "page_token": page_token})
        response = await self._client.request_json("GET", "/wiki/v2/spaces", params=params)
        return _unwrap_data(response)

    async def iter_spaces(self, *, page_size: int = 20) -> AsyncIterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = await self.list_spaces(page_size=page_size, page_token=page_token)
            for item in _iter_page_items(data):
                yield item
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    async def get_space(self, space_id: str, *, lang: Optional[str] = None) -> Mapping[str, Any]:
        params = _drop_none({"lang": lang})
        response = await self._client.request_json("GET", f"/wiki/v2/spaces/{space_id}", params=params)
        return _unwrap_data(response)

    async def get_node(self, token: str, *, obj_type: Optional[str] = None) -> Mapping[str, Any]:
        params = _drop_none({"token": token, "obj_type": obj_type})
        response = await self._client.request_json("GET", "/wiki/v2/spaces/get_node", params=params)
        return _unwrap_data(response)

    async def search_nodes(
        self,
        query: str,
        *,
        space_id: Optional[str] = None,
        node_id: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"page_size": page_size, "page_token": page_token})
        payload = _drop_none({"query": query, "space_id": space_id, "node_id": node_id})
        response = await self._client.request_json(
            "POST",
            "/wiki/v2/nodes/search",
            params=params,
            payload=payload,
        )
        return _unwrap_data(response)

    async def iter_search_nodes(
        self,
        query: str,
        *,
        space_id: Optional[str] = None,
        node_id: Optional[str] = None,
        page_size: int = 20,
    ) -> AsyncIterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = await self.search_nodes(
                query,
                space_id=space_id,
                node_id=node_id,
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

    async def create_node(self, space_id: str, node: Mapping[str, object]) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/wiki/v2/spaces/{space_id}/nodes",
            payload=dict(node),
        )
        return _unwrap_data(response)

    async def list_nodes(
        self,
        space_id: str,
        *,
        parent_node_token: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "parent_node_token": parent_node_token,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        response = await self._client.request_json("GET", f"/wiki/v2/spaces/{space_id}/nodes", params=params)
        return _unwrap_data(response)

    async def iter_nodes(
        self,
        space_id: str,
        *,
        parent_node_token: Optional[str] = None,
        page_size: int = 50,
    ) -> AsyncIterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = await self.list_nodes(
                space_id,
                parent_node_token=parent_node_token,
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

    async def copy_node(
        self,
        space_id: str,
        node_token: str,
        *,
        target_parent_token: Optional[str] = None,
        target_space_id: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Mapping[str, Any]:
        payload = _drop_none(
            {
                "target_parent_token": target_parent_token,
                "target_space_id": target_space_id,
                "title": title,
            }
        )
        response = await self._client.request_json(
            "POST",
            f"/wiki/v2/spaces/{space_id}/nodes/{node_token}/copy",
            payload=payload,
        )
        return _unwrap_data(response)

    async def move_node(
        self,
        space_id: str,
        node_token: str,
        *,
        target_parent_token: Optional[str] = None,
        target_space_id: Optional[str] = None,
    ) -> Mapping[str, Any]:
        payload = _drop_none(
            {
                "target_parent_token": target_parent_token,
                "target_space_id": target_space_id,
            }
        )
        response = await self._client.request_json(
            "POST",
            f"/wiki/v2/spaces/{space_id}/nodes/{node_token}/move",
            payload=payload,
        )
        return _unwrap_data(response)

    async def update_node_title(
        self,
        space_id: str,
        node_token: str,
        *,
        title: str,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/wiki/v2/spaces/{space_id}/nodes/{node_token}/update_title",
            payload={"title": title},
        )
        return _unwrap_data(response)

    async def move_docs_to_wiki(
        self,
        space_id: str,
        *,
        obj_type: str,
        obj_token: str,
        parent_wiki_token: Optional[str] = None,
        apply: Optional[bool] = None,
    ) -> Mapping[str, Any]:
        payload = _drop_none(
            {
                "parent_wiki_token": parent_wiki_token,
                "obj_type": obj_type,
                "obj_token": obj_token,
                "apply": apply,
            }
        )
        response = await self._client.request_json(
            "POST",
            f"/wiki/v2/spaces/{space_id}/nodes/move_docs_to_wiki",
            payload=payload,
        )
        return _unwrap_data(response)

    async def get_task(self, task_id: str, *, task_type: str) -> Mapping[str, Any]:
        params = _drop_none({"task_type": task_type})
        response = await self._client.request_json("GET", f"/wiki/v2/tasks/{task_id}", params=params)
        return _unwrap_data(response)

    async def list_members(
        self,
        space_id: str,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"page_size": page_size, "page_token": page_token})
        response = await self._client.request_json(
            "GET",
            f"/wiki/v2/spaces/{space_id}/members",
            params=params,
        )
        return _unwrap_data(response)

    async def iter_members(self, space_id: str, *, page_size: int = 50) -> AsyncIterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = await self.list_members(space_id, page_size=page_size, page_token=page_token)
            for item in _iter_page_items(data, key="members"):
                yield item
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    async def add_member(
        self,
        space_id: str,
        *,
        member_type: str,
        member_id: str,
        member_role: str,
        collaborator_type: Optional[str] = None,
        need_notification: Optional[bool] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"need_notification": need_notification})
        payload = _drop_none(
            {
                "member_type": member_type,
                "member_id": member_id,
                "member_role": member_role,
                "type": collaborator_type,
            }
        )
        response = await self._client.request_json(
            "POST",
            f"/wiki/v2/spaces/{space_id}/members",
            params=params,
            payload=payload,
        )
        return _unwrap_data(response)

    async def remove_member(
        self,
        space_id: str,
        member_id: str,
        *,
        member_type: str,
        member_role: str,
        collaborator_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        payload = _drop_none(
            {
                "member_type": member_type,
                "member_role": member_role,
                "type": collaborator_type,
            }
        )
        response = await self._client.request_json(
            "DELETE",
            f"/wiki/v2/spaces/{space_id}/members/{member_id}",
            payload=payload,
        )
        return _unwrap_data(response)

    async def update_space_setting(self, space_id: str, setting: Mapping[str, object]) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "PUT",
            f"/wiki/v2/spaces/{space_id}/setting",
            payload=dict(setting),
        )
        return _unwrap_data(response)
