from __future__ import annotations

from typing import Any, AsyncIterator, Mapping, Optional, Sequence

from ._common import (
    _drop_none,
    _has_more,
    _iter_page_items,
    _next_page_token,
    _normalize_ids,
    _normalize_mapping,
    _normalize_mappings,
    _unwrap_data,
)
from ..feishu import AsyncFeishuClient


class AsyncChatService:
    def __init__(self, feishu_client: AsyncFeishuClient) -> None:
        self._client = feishu_client

    async def create_chat(
        self,
        chat: Mapping[str, object],
        *,
        user_id_type: Optional[str] = None,
        set_bot_manager: Optional[bool] = None,
        uuid: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "user_id_type": user_id_type,
                "set_bot_manager": set_bot_manager,
                "uuid": uuid,
            }
        )
        response = await self._client.request_json(
            "POST",
            "/im/v1/chats",
            params=params,
            payload=_normalize_mapping(chat),
        )
        return _unwrap_data(response)

    async def get_chat(self, chat_id: str, *, user_id_type: Optional[str] = None) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "GET",
            f"/im/v1/chats/{chat_id}",
            params=_drop_none({"user_id_type": user_id_type}),
        )
        return _unwrap_data(response)

    async def list_chats(
        self,
        *,
        user_id_type: Optional[str] = None,
        sort_type: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "user_id_type": user_id_type,
                "sort_type": sort_type,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        response = await self._client.request_json("GET", "/im/v1/chats", params=params)
        return _unwrap_data(response)

    async def iter_chats(
        self,
        *,
        user_id_type: Optional[str] = None,
        sort_type: Optional[str] = None,
        page_size: int = 20,
    ) -> AsyncIterator[Any]:
        page_token: Optional[str] = None
        while True:
            data = await self.list_chats(
                user_id_type=user_id_type,
                sort_type=sort_type,
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

    async def search_chats(
        self,
        query: str,
        *,
        user_id_type: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "user_id_type": user_id_type,
                "query": query,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        response = await self._client.request_json("GET", "/im/v1/chats/search", params=params)
        return _unwrap_data(response)

    async def iter_search_chats(
        self,
        query: str,
        *,
        user_id_type: Optional[str] = None,
        page_size: int = 20,
    ) -> AsyncIterator[Any]:
        page_token: Optional[str] = None
        while True:
            data = await self.search_chats(
                query,
                user_id_type=user_id_type,
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

    async def get_moderation(
        self,
        chat_id: str,
        *,
        user_id_type: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "user_id_type": user_id_type,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        response = await self._client.request_json(
            "GET",
            f"/im/v1/chats/{chat_id}/moderation",
            params=params,
        )
        return _unwrap_data(response)

    async def iter_moderation(
        self,
        chat_id: str,
        *,
        user_id_type: Optional[str] = None,
        page_size: int = 50,
    ) -> AsyncIterator[Any]:
        page_token: Optional[str] = None
        while True:
            data = await self.get_moderation(
                chat_id,
                user_id_type=user_id_type,
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

    async def update_moderation(
        self,
        chat_id: str,
        moderation: Mapping[str, object],
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "PUT",
            f"/im/v1/chats/{chat_id}/moderation",
            params=_drop_none({"user_id_type": user_id_type}),
            payload=_normalize_mapping(moderation),
        )
        return _unwrap_data(response)

    async def get_share_link(
        self,
        chat_id: str,
        *,
        validity_period: Optional[str] = None,
    ) -> Mapping[str, Any]:
        payload = _drop_none({"validity_period": validity_period})
        response = await self._client.request_json(
            "POST",
            f"/im/v1/chats/{chat_id}/link",
            payload=payload or None,
        )
        return _unwrap_data(response)

    async def update_chat(
        self,
        chat_id: str,
        chat: Mapping[str, object],
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "PUT",
            f"/im/v1/chats/{chat_id}",
            params=_drop_none({"user_id_type": user_id_type}),
            payload=_normalize_mapping(chat),
        )
        return _unwrap_data(response)

    async def put_top_notice(self, chat_id: str, notice: Mapping[str, object]) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/im/v1/chats/{chat_id}/top_notice/put_top_notice",
            payload=_normalize_mapping(notice),
        )
        return _unwrap_data(response)

    async def delete_top_notice(self, chat_id: str) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/im/v1/chats/{chat_id}/top_notice/delete_top_notice",
        )
        return _unwrap_data(response)

    async def delete_chat(self, chat_id: str) -> Mapping[str, Any]:
        response = await self._client.request_json("DELETE", f"/im/v1/chats/{chat_id}")
        return _unwrap_data(response)

    async def add_managers(
        self,
        chat_id: str,
        manager_ids: Sequence[str],
        *,
        member_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/im/v1/chats/{chat_id}/managers/add_managers",
            params=_drop_none({"member_id_type": member_id_type}),
            payload={"manager_ids": _normalize_ids(manager_ids, name="manager_ids")},
        )
        return _unwrap_data(response)

    async def remove_managers(
        self,
        chat_id: str,
        manager_ids: Sequence[str],
        *,
        member_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/im/v1/chats/{chat_id}/managers/delete_managers",
            params=_drop_none({"member_id_type": member_id_type}),
            payload={"manager_ids": _normalize_ids(manager_ids, name="manager_ids")},
        )
        return _unwrap_data(response)

    async def add_members(
        self,
        chat_id: str,
        member_ids: Sequence[str],
        *,
        member_id_type: Optional[str] = None,
        succeed_type: Optional[int] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "member_id_type": member_id_type,
                "succeed_type": succeed_type,
            }
        )
        response = await self._client.request_json(
            "POST",
            f"/im/v1/chats/{chat_id}/members",
            params=params,
            payload={"id_list": _normalize_ids(member_ids, name="member_ids")},
        )
        return _unwrap_data(response)

    async def remove_members(
        self,
        chat_id: str,
        member_ids: Sequence[str],
        *,
        member_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "DELETE",
            f"/im/v1/chats/{chat_id}/members",
            params=_drop_none({"member_id_type": member_id_type}),
            payload={"id_list": _normalize_ids(member_ids, name="member_ids")},
        )
        return _unwrap_data(response)

    async def join_chat(self, chat_id: str) -> Mapping[str, Any]:
        response = await self._client.request_json("PATCH", f"/im/v1/chats/{chat_id}/members/me_join")
        return _unwrap_data(response)

    async def list_members(
        self,
        chat_id: str,
        *,
        member_id_type: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "member_id_type": member_id_type,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        response = await self._client.request_json(
            "GET",
            f"/im/v1/chats/{chat_id}/members",
            params=params,
        )
        return _unwrap_data(response)

    async def iter_members(
        self,
        chat_id: str,
        *,
        member_id_type: Optional[str] = None,
        page_size: int = 50,
    ) -> AsyncIterator[Any]:
        page_token: Optional[str] = None
        while True:
            data = await self.list_members(
                chat_id,
                member_id_type=member_id_type,
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

    async def check_in_chat(self, chat_id: str) -> Mapping[str, Any]:
        response = await self._client.request_json("GET", f"/im/v1/chats/{chat_id}/members/is_in_chat")
        return _unwrap_data(response)

    async def get_announcement(
        self,
        chat_id: str,
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "GET",
            f"/docx/v1/chats/{chat_id}/announcement",
            params=_drop_none({"user_id_type": user_id_type}),
        )
        return _unwrap_data(response)

    async def list_announcement_blocks(
        self,
        chat_id: str,
        *,
        revision_id: Optional[int] = None,
        user_id_type: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "revision_id": revision_id,
                "user_id_type": user_id_type,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        response = await self._client.request_json(
            "GET",
            f"/docx/v1/chats/{chat_id}/announcement/blocks",
            params=params,
        )
        return _unwrap_data(response)

    async def iter_announcement_blocks(
        self,
        chat_id: str,
        *,
        revision_id: Optional[int] = None,
        user_id_type: Optional[str] = None,
        page_size: int = 200,
    ) -> AsyncIterator[Any]:
        page_token: Optional[str] = None
        while True:
            data = await self.list_announcement_blocks(
                chat_id,
                revision_id=revision_id,
                user_id_type=user_id_type,
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

    async def get_announcement_block(
        self,
        chat_id: str,
        block_id: str,
        *,
        revision_id: Optional[int] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "revision_id": revision_id,
                "user_id_type": user_id_type,
            }
        )
        response = await self._client.request_json(
            "GET",
            f"/docx/v1/chats/{chat_id}/announcement/blocks/{block_id}",
            params=params,
        )
        return _unwrap_data(response)

    async def list_announcement_children(
        self,
        chat_id: str,
        block_id: str,
        *,
        revision_id: Optional[int] = None,
        user_id_type: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "revision_id": revision_id,
                "user_id_type": user_id_type,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        response = await self._client.request_json(
            "GET",
            f"/docx/v1/chats/{chat_id}/announcement/blocks/{block_id}/children",
            params=params,
        )
        return _unwrap_data(response)

    async def iter_announcement_children(
        self,
        chat_id: str,
        block_id: str,
        *,
        revision_id: Optional[int] = None,
        user_id_type: Optional[str] = None,
        page_size: int = 200,
    ) -> AsyncIterator[Any]:
        page_token: Optional[str] = None
        while True:
            data = await self.list_announcement_children(
                chat_id,
                block_id,
                revision_id=revision_id,
                user_id_type=user_id_type,
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

    async def create_announcement_children(
        self,
        chat_id: str,
        block_id: str,
        children: Sequence[Mapping[str, object]],
        *,
        revision_id: Optional[int] = None,
        client_token: Optional[str] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "revision_id": revision_id,
                "client_token": client_token,
                "user_id_type": user_id_type,
            }
        )
        response = await self._client.request_json(
            "POST",
            f"/docx/v1/chats/{chat_id}/announcement/blocks/{block_id}/children",
            params=params,
            payload={"children": _normalize_mappings(children, name="children")},
        )
        return _unwrap_data(response)

    async def batch_update_announcement_blocks(
        self,
        chat_id: str,
        update_request: Mapping[str, object],
        *,
        revision_id: Optional[int] = None,
        client_token: Optional[str] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "revision_id": revision_id,
                "client_token": client_token,
                "user_id_type": user_id_type,
            }
        )
        response = await self._client.request_json(
            "PATCH",
            f"/docx/v1/chats/{chat_id}/announcement/blocks/batch_update",
            params=params,
            payload=_normalize_mapping(update_request),
        )
        return _unwrap_data(response)

    async def delete_announcement_children(
        self,
        chat_id: str,
        block_id: str,
        delete_range: Mapping[str, object],
        *,
        revision_id: Optional[int] = None,
        client_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "revision_id": revision_id,
                "client_token": client_token,
            }
        )
        response = await self._client.request_json(
            "DELETE",
            f"/docx/v1/chats/{chat_id}/announcement/blocks/{block_id}/children/batch_delete",
            params=params,
            payload=_normalize_mapping(delete_range),
        )
        return _unwrap_data(response)

    async def create_tabs(self, chat_id: str, tabs: Sequence[Mapping[str, object]]) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/im/v1/chats/{chat_id}/chat_tabs",
            payload={"chat_tabs": _normalize_mappings(tabs, name="chat_tabs")},
        )
        return _unwrap_data(response)

    async def update_tabs(self, chat_id: str, tabs: Sequence[Mapping[str, object]]) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/im/v1/chats/{chat_id}/chat_tabs/update_tabs",
            payload={"chat_tabs": _normalize_mappings(tabs, name="chat_tabs")},
        )
        return _unwrap_data(response)

    async def sort_tabs(self, chat_id: str, tab_ids: Sequence[str]) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/im/v1/chats/{chat_id}/chat_tabs/sort_tabs",
            payload={"tab_ids": _normalize_ids(tab_ids, name="tab_ids")},
        )
        return _unwrap_data(response)

    async def list_tabs(self, chat_id: str) -> Mapping[str, Any]:
        response = await self._client.request_json("GET", f"/im/v1/chats/{chat_id}/chat_tabs/list_tabs")
        return _unwrap_data(response)

    async def delete_tabs(self, chat_id: str, tab_ids: Sequence[str]) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "DELETE",
            f"/im/v1/chats/{chat_id}/chat_tabs/delete_tabs",
            payload={"tab_ids": _normalize_ids(tab_ids, name="tab_ids")},
        )
        return _unwrap_data(response)

    async def create_menu(self, chat_id: str, menu_tree: Mapping[str, object]) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/im/v1/chats/{chat_id}/menu_tree",
            payload={"menu_tree": _normalize_mapping(menu_tree)},
        )
        return _unwrap_data(response)

    async def get_menu(self, chat_id: str) -> Mapping[str, Any]:
        response = await self._client.request_json("GET", f"/im/v1/chats/{chat_id}/menu_tree")
        return _unwrap_data(response)

    async def update_menu_item(
        self,
        chat_id: str,
        menu_item_id: str,
        menu_item_update: Mapping[str, object],
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "PATCH",
            f"/im/v1/chats/{chat_id}/menu_items/{menu_item_id}",
            payload=_normalize_mapping(menu_item_update),
        )
        return _unwrap_data(response)

    async def sort_menu(self, chat_id: str, top_level_ids: Sequence[str]) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/im/v1/chats/{chat_id}/menu_tree/sort",
            payload={"chat_menu_top_level_ids": _normalize_ids(top_level_ids, name="top_level_ids")},
        )
        return _unwrap_data(response)

    async def delete_menu(self, chat_id: str, top_level_ids: Sequence[str]) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "DELETE",
            f"/im/v1/chats/{chat_id}/menu_tree",
            payload={"chat_menu_top_level_ids": _normalize_ids(top_level_ids, name="top_level_ids")},
        )
        return _unwrap_data(response)


__all__ = ["AsyncChatService"]
