from __future__ import annotations

from typing import Any, AsyncIterator, Iterator, Mapping, Optional, Sequence

from ._common import (
    _drop_none,
    _has_more,
    _iter_items,
    _next_page_token,
    _normalize_mapping,
    _normalize_mappings,
    _normalize_strings,
    _unwrap_data,
)
from ..feishu import AsyncFeishuClient, FeishuClient


class PublicMailboxService:
    def __init__(self, feishu_client: FeishuClient) -> None:
        self._client = feishu_client

    def list_public_mailboxes(
        self,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "GET",
            "/mail/v1/public_mailboxes",
            params=_drop_none({"page_size": page_size, "page_token": page_token}),
        )
        return _unwrap_data(response)

    def iter_public_mailboxes(self, *, page_size: int = 50) -> Iterator[Any]:
        page_token: Optional[str] = None
        while True:
            data = self.list_public_mailboxes(page_size=page_size, page_token=page_token)
            yield from _iter_items(data)
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    def get_public_mailbox(self, public_mailbox_id: str) -> Mapping[str, Any]:
        response = self._client.request_json("GET", f"/mail/v1/public_mailboxes/{public_mailbox_id}")
        return _unwrap_data(response)

    def create_public_mailbox(self, public_mailbox: Mapping[str, object]) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            "/mail/v1/public_mailboxes",
            payload=_normalize_mapping(public_mailbox),
        )
        return _unwrap_data(response)

    def update_public_mailbox(
        self,
        public_mailbox_id: str,
        public_mailbox: Mapping[str, object],
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "PATCH",
            f"/mail/v1/public_mailboxes/{public_mailbox_id}",
            payload=_normalize_mapping(public_mailbox),
        )
        return _unwrap_data(response)

    def replace_public_mailbox(
        self,
        public_mailbox_id: str,
        public_mailbox: Mapping[str, object],
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "PUT",
            f"/mail/v1/public_mailboxes/{public_mailbox_id}",
            payload=_normalize_mapping(public_mailbox),
        )
        return _unwrap_data(response)

    def delete_public_mailbox(self, public_mailbox_id: str) -> Mapping[str, Any]:
        response = self._client.request_json("DELETE", f"/mail/v1/public_mailboxes/{public_mailbox_id}")
        return _unwrap_data(response)

    def remove_to_recycle_bin(
        self,
        public_mailbox_id: str,
        options: Optional[Mapping[str, object]] = None,
    ) -> Mapping[str, Any]:
        payload = _normalize_mapping(options) if options is not None else None
        response = self._client.request_json(
            "DELETE",
            f"/mail/v1/public_mailboxes/{public_mailbox_id}/remove_to_recycle_bin",
            payload=payload,
        )
        return _unwrap_data(response)


class AsyncPublicMailboxService:
    def __init__(self, feishu_client: AsyncFeishuClient) -> None:
        self._client = feishu_client

    async def list_public_mailboxes(
        self,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "GET",
            "/mail/v1/public_mailboxes",
            params=_drop_none({"page_size": page_size, "page_token": page_token}),
        )
        return _unwrap_data(response)

    async def iter_public_mailboxes(self, *, page_size: int = 50) -> AsyncIterator[Any]:
        page_token: Optional[str] = None
        while True:
            data = await self.list_public_mailboxes(page_size=page_size, page_token=page_token)
            for item in _iter_items(data):
                yield item
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    async def get_public_mailbox(self, public_mailbox_id: str) -> Mapping[str, Any]:
        response = await self._client.request_json("GET", f"/mail/v1/public_mailboxes/{public_mailbox_id}")
        return _unwrap_data(response)

    async def create_public_mailbox(self, public_mailbox: Mapping[str, object]) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            "/mail/v1/public_mailboxes",
            payload=_normalize_mapping(public_mailbox),
        )
        return _unwrap_data(response)

    async def update_public_mailbox(
        self,
        public_mailbox_id: str,
        public_mailbox: Mapping[str, object],
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "PATCH",
            f"/mail/v1/public_mailboxes/{public_mailbox_id}",
            payload=_normalize_mapping(public_mailbox),
        )
        return _unwrap_data(response)

    async def replace_public_mailbox(
        self,
        public_mailbox_id: str,
        public_mailbox: Mapping[str, object],
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "PUT",
            f"/mail/v1/public_mailboxes/{public_mailbox_id}",
            payload=_normalize_mapping(public_mailbox),
        )
        return _unwrap_data(response)

    async def delete_public_mailbox(self, public_mailbox_id: str) -> Mapping[str, Any]:
        response = await self._client.request_json("DELETE", f"/mail/v1/public_mailboxes/{public_mailbox_id}")
        return _unwrap_data(response)

    async def remove_to_recycle_bin(
        self,
        public_mailbox_id: str,
        options: Optional[Mapping[str, object]] = None,
    ) -> Mapping[str, Any]:
        payload = _normalize_mapping(options) if options is not None else None
        response = await self._client.request_json(
            "DELETE",
            f"/mail/v1/public_mailboxes/{public_mailbox_id}/remove_to_recycle_bin",
            payload=payload,
        )
        return _unwrap_data(response)


class PublicMailboxAliasService:
    def __init__(self, feishu_client: FeishuClient) -> None:
        self._client = feishu_client

    def list_aliases(self, public_mailbox_id: str) -> Mapping[str, Any]:
        response = self._client.request_json("GET", f"/mail/v1/public_mailboxes/{public_mailbox_id}/aliases")
        return _unwrap_data(response)

    def create_alias(self, public_mailbox_id: str, alias: Mapping[str, object]) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            f"/mail/v1/public_mailboxes/{public_mailbox_id}/aliases",
            payload=_normalize_mapping(alias),
        )
        return _unwrap_data(response)

    def delete_alias(self, public_mailbox_id: str, alias_id: str) -> Mapping[str, Any]:
        response = self._client.request_json(
            "DELETE",
            f"/mail/v1/public_mailboxes/{public_mailbox_id}/aliases/{alias_id}",
        )
        return _unwrap_data(response)


class AsyncPublicMailboxAliasService:
    def __init__(self, feishu_client: AsyncFeishuClient) -> None:
        self._client = feishu_client

    async def list_aliases(self, public_mailbox_id: str) -> Mapping[str, Any]:
        response = await self._client.request_json("GET", f"/mail/v1/public_mailboxes/{public_mailbox_id}/aliases")
        return _unwrap_data(response)

    async def create_alias(self, public_mailbox_id: str, alias: Mapping[str, object]) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/mail/v1/public_mailboxes/{public_mailbox_id}/aliases",
            payload=_normalize_mapping(alias),
        )
        return _unwrap_data(response)

    async def delete_alias(self, public_mailbox_id: str, alias_id: str) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "DELETE",
            f"/mail/v1/public_mailboxes/{public_mailbox_id}/aliases/{alias_id}",
        )
        return _unwrap_data(response)


class PublicMailboxMemberService:
    def __init__(self, feishu_client: FeishuClient) -> None:
        self._client = feishu_client

    def list_members(
        self,
        public_mailbox_id: str,
        *,
        user_id_type: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "GET",
            f"/mail/v1/public_mailboxes/{public_mailbox_id}/members",
            params=_drop_none(
                {
                    "user_id_type": user_id_type,
                    "page_size": page_size,
                    "page_token": page_token,
                }
            ),
        )
        return _unwrap_data(response)

    def iter_members(
        self,
        public_mailbox_id: str,
        *,
        user_id_type: Optional[str] = None,
        page_size: int = 50,
    ) -> Iterator[Any]:
        page_token: Optional[str] = None
        while True:
            data = self.list_members(
                public_mailbox_id,
                user_id_type=user_id_type,
                page_size=page_size,
                page_token=page_token,
            )
            yield from _iter_items(data)
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    def get_member(
        self,
        public_mailbox_id: str,
        member_id: str,
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "GET",
            f"/mail/v1/public_mailboxes/{public_mailbox_id}/members/{member_id}",
            params=_drop_none({"user_id_type": user_id_type}),
        )
        return _unwrap_data(response)

    def create_member(
        self,
        public_mailbox_id: str,
        member: Mapping[str, object],
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            f"/mail/v1/public_mailboxes/{public_mailbox_id}/members",
            params=_drop_none({"user_id_type": user_id_type}),
            payload=_normalize_mapping(member),
        )
        return _unwrap_data(response)

    def batch_create_members(
        self,
        public_mailbox_id: str,
        items: Sequence[Mapping[str, object]],
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            f"/mail/v1/public_mailboxes/{public_mailbox_id}/members/batch_create",
            params=_drop_none({"user_id_type": user_id_type}),
            payload={"items": _normalize_mappings(items, name="items")},
        )
        return _unwrap_data(response)

    def delete_member(
        self,
        public_mailbox_id: str,
        member_id: str,
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "DELETE",
            f"/mail/v1/public_mailboxes/{public_mailbox_id}/members/{member_id}",
            params=_drop_none({"user_id_type": user_id_type}),
        )
        return _unwrap_data(response)

    def batch_delete_members(
        self,
        public_mailbox_id: str,
        member_id_list: Sequence[str],
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "DELETE",
            f"/mail/v1/public_mailboxes/{public_mailbox_id}/members/batch_delete",
            params=_drop_none({"user_id_type": user_id_type}),
            payload={"member_id_list": _normalize_strings(member_id_list, name="member_id_list")},
        )
        return _unwrap_data(response)

    def clear_members(self, public_mailbox_id: str) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            f"/mail/v1/public_mailboxes/{public_mailbox_id}/members/clear",
        )
        return _unwrap_data(response)


class AsyncPublicMailboxMemberService:
    def __init__(self, feishu_client: AsyncFeishuClient) -> None:
        self._client = feishu_client

    async def list_members(
        self,
        public_mailbox_id: str,
        *,
        user_id_type: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "GET",
            f"/mail/v1/public_mailboxes/{public_mailbox_id}/members",
            params=_drop_none(
                {
                    "user_id_type": user_id_type,
                    "page_size": page_size,
                    "page_token": page_token,
                }
            ),
        )
        return _unwrap_data(response)

    async def iter_members(
        self,
        public_mailbox_id: str,
        *,
        user_id_type: Optional[str] = None,
        page_size: int = 50,
    ) -> AsyncIterator[Any]:
        page_token: Optional[str] = None
        while True:
            data = await self.list_members(
                public_mailbox_id,
                user_id_type=user_id_type,
                page_size=page_size,
                page_token=page_token,
            )
            for item in _iter_items(data):
                yield item
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    async def get_member(
        self,
        public_mailbox_id: str,
        member_id: str,
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "GET",
            f"/mail/v1/public_mailboxes/{public_mailbox_id}/members/{member_id}",
            params=_drop_none({"user_id_type": user_id_type}),
        )
        return _unwrap_data(response)

    async def create_member(
        self,
        public_mailbox_id: str,
        member: Mapping[str, object],
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/mail/v1/public_mailboxes/{public_mailbox_id}/members",
            params=_drop_none({"user_id_type": user_id_type}),
            payload=_normalize_mapping(member),
        )
        return _unwrap_data(response)

    async def batch_create_members(
        self,
        public_mailbox_id: str,
        items: Sequence[Mapping[str, object]],
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/mail/v1/public_mailboxes/{public_mailbox_id}/members/batch_create",
            params=_drop_none({"user_id_type": user_id_type}),
            payload={"items": _normalize_mappings(items, name="items")},
        )
        return _unwrap_data(response)

    async def delete_member(
        self,
        public_mailbox_id: str,
        member_id: str,
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "DELETE",
            f"/mail/v1/public_mailboxes/{public_mailbox_id}/members/{member_id}",
            params=_drop_none({"user_id_type": user_id_type}),
        )
        return _unwrap_data(response)

    async def batch_delete_members(
        self,
        public_mailbox_id: str,
        member_id_list: Sequence[str],
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "DELETE",
            f"/mail/v1/public_mailboxes/{public_mailbox_id}/members/batch_delete",
            params=_drop_none({"user_id_type": user_id_type}),
            payload={"member_id_list": _normalize_strings(member_id_list, name="member_id_list")},
        )
        return _unwrap_data(response)

    async def clear_members(self, public_mailbox_id: str) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/mail/v1/public_mailboxes/{public_mailbox_id}/members/clear",
        )
        return _unwrap_data(response)


__all__ = [
    "PublicMailboxService",
    "AsyncPublicMailboxService",
    "PublicMailboxAliasService",
    "AsyncPublicMailboxAliasService",
    "PublicMailboxMemberService",
    "AsyncPublicMailboxMemberService",
]
