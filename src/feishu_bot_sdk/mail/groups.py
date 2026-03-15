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


class MailGroupService:
    def __init__(self, feishu_client: FeishuClient) -> None:
        self._client = feishu_client

    def list_mailgroups(
        self,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "GET",
            "/mail/v1/mailgroups",
            params=_drop_none({"page_size": page_size, "page_token": page_token}),
        )
        return _unwrap_data(response)

    def iter_mailgroups(self, *, page_size: int = 50) -> Iterator[Any]:
        page_token: Optional[str] = None
        while True:
            data = self.list_mailgroups(page_size=page_size, page_token=page_token)
            yield from _iter_items(data)
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    def get_mailgroup(self, mailgroup_id: str) -> Mapping[str, Any]:
        response = self._client.request_json("GET", f"/mail/v1/mailgroups/{mailgroup_id}")
        return _unwrap_data(response)

    def create_mailgroup(self, mailgroup: Mapping[str, object]) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            "/mail/v1/mailgroups",
            payload=_normalize_mapping(mailgroup),
        )
        return _unwrap_data(response)

    def update_mailgroup(self, mailgroup_id: str, mailgroup: Mapping[str, object]) -> Mapping[str, Any]:
        response = self._client.request_json(
            "PATCH",
            f"/mail/v1/mailgroups/{mailgroup_id}",
            payload=_normalize_mapping(mailgroup),
        )
        return _unwrap_data(response)

    def replace_mailgroup(self, mailgroup_id: str, mailgroup: Mapping[str, object]) -> Mapping[str, Any]:
        response = self._client.request_json(
            "PUT",
            f"/mail/v1/mailgroups/{mailgroup_id}",
            payload=_normalize_mapping(mailgroup),
        )
        return _unwrap_data(response)

    def delete_mailgroup(self, mailgroup_id: str) -> Mapping[str, Any]:
        response = self._client.request_json("DELETE", f"/mail/v1/mailgroups/{mailgroup_id}")
        return _unwrap_data(response)


class AsyncMailGroupService:
    def __init__(self, feishu_client: AsyncFeishuClient) -> None:
        self._client = feishu_client

    async def list_mailgroups(
        self,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "GET",
            "/mail/v1/mailgroups",
            params=_drop_none({"page_size": page_size, "page_token": page_token}),
        )
        return _unwrap_data(response)

    async def iter_mailgroups(self, *, page_size: int = 50) -> AsyncIterator[Any]:
        page_token: Optional[str] = None
        while True:
            data = await self.list_mailgroups(page_size=page_size, page_token=page_token)
            for item in _iter_items(data):
                yield item
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    async def get_mailgroup(self, mailgroup_id: str) -> Mapping[str, Any]:
        response = await self._client.request_json("GET", f"/mail/v1/mailgroups/{mailgroup_id}")
        return _unwrap_data(response)

    async def create_mailgroup(self, mailgroup: Mapping[str, object]) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            "/mail/v1/mailgroups",
            payload=_normalize_mapping(mailgroup),
        )
        return _unwrap_data(response)

    async def update_mailgroup(self, mailgroup_id: str, mailgroup: Mapping[str, object]) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "PATCH",
            f"/mail/v1/mailgroups/{mailgroup_id}",
            payload=_normalize_mapping(mailgroup),
        )
        return _unwrap_data(response)

    async def replace_mailgroup(self, mailgroup_id: str, mailgroup: Mapping[str, object]) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "PUT",
            f"/mail/v1/mailgroups/{mailgroup_id}",
            payload=_normalize_mapping(mailgroup),
        )
        return _unwrap_data(response)

    async def delete_mailgroup(self, mailgroup_id: str) -> Mapping[str, Any]:
        response = await self._client.request_json("DELETE", f"/mail/v1/mailgroups/{mailgroup_id}")
        return _unwrap_data(response)


class MailGroupAliasService:
    def __init__(self, feishu_client: FeishuClient) -> None:
        self._client = feishu_client

    def list_aliases(self, mailgroup_id: str) -> Mapping[str, Any]:
        response = self._client.request_json("GET", f"/mail/v1/mailgroups/{mailgroup_id}/aliases")
        return _unwrap_data(response)

    def create_alias(self, mailgroup_id: str, alias: Mapping[str, object]) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            f"/mail/v1/mailgroups/{mailgroup_id}/aliases",
            payload=_normalize_mapping(alias),
        )
        return _unwrap_data(response)

    def delete_alias(self, mailgroup_id: str, alias_id: str) -> Mapping[str, Any]:
        response = self._client.request_json(
            "DELETE",
            f"/mail/v1/mailgroups/{mailgroup_id}/aliases/{alias_id}",
        )
        return _unwrap_data(response)


class AsyncMailGroupAliasService:
    def __init__(self, feishu_client: AsyncFeishuClient) -> None:
        self._client = feishu_client

    async def list_aliases(self, mailgroup_id: str) -> Mapping[str, Any]:
        response = await self._client.request_json("GET", f"/mail/v1/mailgroups/{mailgroup_id}/aliases")
        return _unwrap_data(response)

    async def create_alias(self, mailgroup_id: str, alias: Mapping[str, object]) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/mail/v1/mailgroups/{mailgroup_id}/aliases",
            payload=_normalize_mapping(alias),
        )
        return _unwrap_data(response)

    async def delete_alias(self, mailgroup_id: str, alias_id: str) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "DELETE",
            f"/mail/v1/mailgroups/{mailgroup_id}/aliases/{alias_id}",
        )
        return _unwrap_data(response)


class MailGroupMemberService:
    def __init__(self, feishu_client: FeishuClient) -> None:
        self._client = feishu_client

    def list_members(
        self,
        mailgroup_id: str,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "user_id_type": user_id_type,
                "department_id_type": department_id_type,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        response = self._client.request_json(
            "GET",
            f"/mail/v1/mailgroups/{mailgroup_id}/members",
            params=params,
        )
        return _unwrap_data(response)

    def iter_members(
        self,
        mailgroup_id: str,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
        page_size: int = 50,
    ) -> Iterator[Any]:
        page_token: Optional[str] = None
        while True:
            data = self.list_members(
                mailgroup_id,
                user_id_type=user_id_type,
                department_id_type=department_id_type,
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
        mailgroup_id: str,
        member_id: str,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "GET",
            f"/mail/v1/mailgroups/{mailgroup_id}/members/{member_id}",
            params=_drop_none(
                {
                    "user_id_type": user_id_type,
                    "department_id_type": department_id_type,
                }
            ),
        )
        return _unwrap_data(response)

    def create_member(
        self,
        mailgroup_id: str,
        member: Mapping[str, object],
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            f"/mail/v1/mailgroups/{mailgroup_id}/members",
            params=_drop_none(
                {
                    "user_id_type": user_id_type,
                    "department_id_type": department_id_type,
                }
            ),
            payload=_normalize_mapping(member),
        )
        return _unwrap_data(response)

    def batch_create_members(
        self,
        mailgroup_id: str,
        items: Sequence[Mapping[str, object]],
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            f"/mail/v1/mailgroups/{mailgroup_id}/members/batch_create",
            params=_drop_none(
                {
                    "user_id_type": user_id_type,
                    "department_id_type": department_id_type,
                }
            ),
            payload={"items": _normalize_mappings(items, name="items")},
        )
        return _unwrap_data(response)

    def delete_member(
        self,
        mailgroup_id: str,
        member_id: str,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "DELETE",
            f"/mail/v1/mailgroups/{mailgroup_id}/members/{member_id}",
            params=_drop_none(
                {
                    "user_id_type": user_id_type,
                    "department_id_type": department_id_type,
                }
            ),
        )
        return _unwrap_data(response)

    def batch_delete_members(
        self,
        mailgroup_id: str,
        member_id_list: Sequence[str],
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "DELETE",
            f"/mail/v1/mailgroups/{mailgroup_id}/members/batch_delete",
            params=_drop_none(
                {
                    "user_id_type": user_id_type,
                    "department_id_type": department_id_type,
                }
            ),
            payload={"member_id_list": _normalize_strings(member_id_list, name="member_id_list")},
        )
        return _unwrap_data(response)


class AsyncMailGroupMemberService:
    def __init__(self, feishu_client: AsyncFeishuClient) -> None:
        self._client = feishu_client

    async def list_members(
        self,
        mailgroup_id: str,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "user_id_type": user_id_type,
                "department_id_type": department_id_type,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        response = await self._client.request_json(
            "GET",
            f"/mail/v1/mailgroups/{mailgroup_id}/members",
            params=params,
        )
        return _unwrap_data(response)

    async def iter_members(
        self,
        mailgroup_id: str,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
        page_size: int = 50,
    ) -> AsyncIterator[Any]:
        page_token: Optional[str] = None
        while True:
            data = await self.list_members(
                mailgroup_id,
                user_id_type=user_id_type,
                department_id_type=department_id_type,
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
        mailgroup_id: str,
        member_id: str,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "GET",
            f"/mail/v1/mailgroups/{mailgroup_id}/members/{member_id}",
            params=_drop_none(
                {
                    "user_id_type": user_id_type,
                    "department_id_type": department_id_type,
                }
            ),
        )
        return _unwrap_data(response)

    async def create_member(
        self,
        mailgroup_id: str,
        member: Mapping[str, object],
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/mail/v1/mailgroups/{mailgroup_id}/members",
            params=_drop_none(
                {
                    "user_id_type": user_id_type,
                    "department_id_type": department_id_type,
                }
            ),
            payload=_normalize_mapping(member),
        )
        return _unwrap_data(response)

    async def batch_create_members(
        self,
        mailgroup_id: str,
        items: Sequence[Mapping[str, object]],
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/mail/v1/mailgroups/{mailgroup_id}/members/batch_create",
            params=_drop_none(
                {
                    "user_id_type": user_id_type,
                    "department_id_type": department_id_type,
                }
            ),
            payload={"items": _normalize_mappings(items, name="items")},
        )
        return _unwrap_data(response)

    async def delete_member(
        self,
        mailgroup_id: str,
        member_id: str,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "DELETE",
            f"/mail/v1/mailgroups/{mailgroup_id}/members/{member_id}",
            params=_drop_none(
                {
                    "user_id_type": user_id_type,
                    "department_id_type": department_id_type,
                }
            ),
        )
        return _unwrap_data(response)

    async def batch_delete_members(
        self,
        mailgroup_id: str,
        member_id_list: Sequence[str],
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "DELETE",
            f"/mail/v1/mailgroups/{mailgroup_id}/members/batch_delete",
            params=_drop_none(
                {
                    "user_id_type": user_id_type,
                    "department_id_type": department_id_type,
                }
            ),
            payload={"member_id_list": _normalize_strings(member_id_list, name="member_id_list")},
        )
        return _unwrap_data(response)


class MailGroupPermissionMemberService:
    def __init__(self, feishu_client: FeishuClient) -> None:
        self._client = feishu_client

    def list_permission_members(
        self,
        mailgroup_id: str,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "user_id_type": user_id_type,
                "department_id_type": department_id_type,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        response = self._client.request_json(
            "GET",
            f"/mail/v1/mailgroups/{mailgroup_id}/permission_members",
            params=params,
        )
        return _unwrap_data(response)

    def iter_permission_members(
        self,
        mailgroup_id: str,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
        page_size: int = 50,
    ) -> Iterator[Any]:
        page_token: Optional[str] = None
        while True:
            data = self.list_permission_members(
                mailgroup_id,
                user_id_type=user_id_type,
                department_id_type=department_id_type,
                page_size=page_size,
                page_token=page_token,
            )
            yield from _iter_items(data)
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    def get_permission_member(
        self,
        mailgroup_id: str,
        member_id: str,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "GET",
            f"/mail/v1/mailgroups/{mailgroup_id}/permission_members/{member_id}",
            params=_drop_none(
                {
                    "user_id_type": user_id_type,
                    "department_id_type": department_id_type,
                }
            ),
        )
        return _unwrap_data(response)

    def create_permission_member(
        self,
        mailgroup_id: str,
        member: Mapping[str, object],
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            f"/mail/v1/mailgroups/{mailgroup_id}/permission_members",
            params=_drop_none(
                {
                    "user_id_type": user_id_type,
                    "department_id_type": department_id_type,
                }
            ),
            payload=_normalize_mapping(member),
        )
        return _unwrap_data(response)

    def batch_create_permission_members(
        self,
        mailgroup_id: str,
        items: Sequence[Mapping[str, object]],
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            f"/mail/v1/mailgroups/{mailgroup_id}/permission_members/batch_create",
            params=_drop_none(
                {
                    "user_id_type": user_id_type,
                    "department_id_type": department_id_type,
                }
            ),
            payload={"items": _normalize_mappings(items, name="items")},
        )
        return _unwrap_data(response)

    def delete_permission_member(
        self,
        mailgroup_id: str,
        member_id: str,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "DELETE",
            f"/mail/v1/mailgroups/{mailgroup_id}/permission_members/{member_id}",
            params=_drop_none(
                {
                    "user_id_type": user_id_type,
                    "department_id_type": department_id_type,
                }
            ),
        )
        return _unwrap_data(response)

    def batch_delete_permission_members(
        self,
        mailgroup_id: str,
        member_id_list: Sequence[str],
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "DELETE",
            f"/mail/v1/mailgroups/{mailgroup_id}/permission_members/batch_delete",
            params=_drop_none(
                {
                    "user_id_type": user_id_type,
                    "department_id_type": department_id_type,
                }
            ),
            payload={"member_id_list": _normalize_strings(member_id_list, name="member_id_list")},
        )
        return _unwrap_data(response)


class AsyncMailGroupPermissionMemberService:
    def __init__(self, feishu_client: AsyncFeishuClient) -> None:
        self._client = feishu_client

    async def list_permission_members(
        self,
        mailgroup_id: str,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "user_id_type": user_id_type,
                "department_id_type": department_id_type,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        response = await self._client.request_json(
            "GET",
            f"/mail/v1/mailgroups/{mailgroup_id}/permission_members",
            params=params,
        )
        return _unwrap_data(response)

    async def iter_permission_members(
        self,
        mailgroup_id: str,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
        page_size: int = 50,
    ) -> AsyncIterator[Any]:
        page_token: Optional[str] = None
        while True:
            data = await self.list_permission_members(
                mailgroup_id,
                user_id_type=user_id_type,
                department_id_type=department_id_type,
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

    async def get_permission_member(
        self,
        mailgroup_id: str,
        member_id: str,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "GET",
            f"/mail/v1/mailgroups/{mailgroup_id}/permission_members/{member_id}",
            params=_drop_none(
                {
                    "user_id_type": user_id_type,
                    "department_id_type": department_id_type,
                }
            ),
        )
        return _unwrap_data(response)

    async def create_permission_member(
        self,
        mailgroup_id: str,
        member: Mapping[str, object],
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/mail/v1/mailgroups/{mailgroup_id}/permission_members",
            params=_drop_none(
                {
                    "user_id_type": user_id_type,
                    "department_id_type": department_id_type,
                }
            ),
            payload=_normalize_mapping(member),
        )
        return _unwrap_data(response)

    async def batch_create_permission_members(
        self,
        mailgroup_id: str,
        items: Sequence[Mapping[str, object]],
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/mail/v1/mailgroups/{mailgroup_id}/permission_members/batch_create",
            params=_drop_none(
                {
                    "user_id_type": user_id_type,
                    "department_id_type": department_id_type,
                }
            ),
            payload={"items": _normalize_mappings(items, name="items")},
        )
        return _unwrap_data(response)

    async def delete_permission_member(
        self,
        mailgroup_id: str,
        member_id: str,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "DELETE",
            f"/mail/v1/mailgroups/{mailgroup_id}/permission_members/{member_id}",
            params=_drop_none(
                {
                    "user_id_type": user_id_type,
                    "department_id_type": department_id_type,
                }
            ),
        )
        return _unwrap_data(response)

    async def batch_delete_permission_members(
        self,
        mailgroup_id: str,
        member_id_list: Sequence[str],
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "DELETE",
            f"/mail/v1/mailgroups/{mailgroup_id}/permission_members/batch_delete",
            params=_drop_none(
                {
                    "user_id_type": user_id_type,
                    "department_id_type": department_id_type,
                }
            ),
            payload={"member_id_list": _normalize_strings(member_id_list, name="member_id_list")},
        )
        return _unwrap_data(response)


class MailGroupManagerService:
    def __init__(self, feishu_client: FeishuClient) -> None:
        self._client = feishu_client

    def list_managers(
        self,
        mailgroup_id: str,
        *,
        user_id_type: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "GET",
            f"/mail/v1/mailgroups/{mailgroup_id}/managers",
            params=_drop_none(
                {
                    "user_id_type": user_id_type,
                    "page_size": page_size,
                    "page_token": page_token,
                }
            ),
        )
        return _unwrap_data(response)

    def iter_managers(
        self,
        mailgroup_id: str,
        *,
        user_id_type: Optional[str] = None,
        page_size: int = 50,
    ) -> Iterator[Any]:
        page_token: Optional[str] = None
        while True:
            data = self.list_managers(
                mailgroup_id,
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

    def batch_create_managers(
        self,
        mailgroup_id: str,
        mailgroup_manager_list: Sequence[Mapping[str, object]],
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            f"/mail/v1/mailgroups/{mailgroup_id}/managers/batch_create",
            params=_drop_none({"user_id_type": user_id_type}),
            payload={"mailgroup_manager_list": _normalize_mappings(mailgroup_manager_list, name="mailgroup_manager_list")},
        )
        return _unwrap_data(response)

    def batch_delete_managers(
        self,
        mailgroup_id: str,
        mailgroup_manager_list: Sequence[Mapping[str, object]],
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            f"/mail/v1/mailgroups/{mailgroup_id}/managers/batch_delete",
            params=_drop_none({"user_id_type": user_id_type}),
            payload={"mailgroup_manager_list": _normalize_mappings(mailgroup_manager_list, name="mailgroup_manager_list")},
        )
        return _unwrap_data(response)


class AsyncMailGroupManagerService:
    def __init__(self, feishu_client: AsyncFeishuClient) -> None:
        self._client = feishu_client

    async def list_managers(
        self,
        mailgroup_id: str,
        *,
        user_id_type: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "GET",
            f"/mail/v1/mailgroups/{mailgroup_id}/managers",
            params=_drop_none(
                {
                    "user_id_type": user_id_type,
                    "page_size": page_size,
                    "page_token": page_token,
                }
            ),
        )
        return _unwrap_data(response)

    async def iter_managers(
        self,
        mailgroup_id: str,
        *,
        user_id_type: Optional[str] = None,
        page_size: int = 50,
    ) -> AsyncIterator[Any]:
        page_token: Optional[str] = None
        while True:
            data = await self.list_managers(
                mailgroup_id,
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

    async def batch_create_managers(
        self,
        mailgroup_id: str,
        mailgroup_manager_list: Sequence[Mapping[str, object]],
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/mail/v1/mailgroups/{mailgroup_id}/managers/batch_create",
            params=_drop_none({"user_id_type": user_id_type}),
            payload={"mailgroup_manager_list": _normalize_mappings(mailgroup_manager_list, name="mailgroup_manager_list")},
        )
        return _unwrap_data(response)

    async def batch_delete_managers(
        self,
        mailgroup_id: str,
        mailgroup_manager_list: Sequence[Mapping[str, object]],
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/mail/v1/mailgroups/{mailgroup_id}/managers/batch_delete",
            params=_drop_none({"user_id_type": user_id_type}),
            payload={"mailgroup_manager_list": _normalize_mappings(mailgroup_manager_list, name="mailgroup_manager_list")},
        )
        return _unwrap_data(response)


__all__ = [
    "MailGroupService",
    "AsyncMailGroupService",
    "MailGroupAliasService",
    "AsyncMailGroupAliasService",
    "MailGroupMemberService",
    "AsyncMailGroupMemberService",
    "MailGroupPermissionMemberService",
    "AsyncMailGroupPermissionMemberService",
    "MailGroupManagerService",
    "AsyncMailGroupManagerService",
]
