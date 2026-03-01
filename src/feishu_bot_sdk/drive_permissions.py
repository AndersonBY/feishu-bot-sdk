from typing import Any, Mapping, Optional

from .exceptions import FeishuError
from .feishu import AsyncFeishuClient, FeishuClient
from .response import DataResponse
from .types import DriveResourceType, MemberIdType


_MEMBER_TYPE_MAP = {
    MemberIdType.OPEN_ID.value: "openid",
    MemberIdType.USER_ID.value: "userid",
    MemberIdType.UNION_ID.value: "unionid",
}


def _drop_none(params: Mapping[str, object]) -> dict[str, object]:
    return {key: value for key, value in params.items() if value is not None}


def _unwrap_data(response: Mapping[str, Any]) -> DataResponse:
    return DataResponse.from_raw(response)


def _member_type(member_id_type: str) -> str:
    return _MEMBER_TYPE_MAP.get(member_id_type, "openid")


def _resource_type(resource_type: str | DriveResourceType) -> str:
    if isinstance(resource_type, DriveResourceType):
        return resource_type.value
    return resource_type


class DrivePermissionService:
    def __init__(self, feishu_client: FeishuClient) -> None:
        self._client = feishu_client

    def grant_edit_permission(
        self,
        token: str,
        member_id: str,
        member_id_type: str = MemberIdType.OPEN_ID.value,
        *,
        resource_type: str | DriveResourceType,
        permission: str,
    ) -> None:
        try:
            self.add_member(
                token,
                resource_type=resource_type,
                member_id=member_id,
                member_id_type=member_id_type,
                perm=permission,
            )
            return
        except FeishuError:
            self.update_member(
                token,
                member_id,
                resource_type=resource_type,
                member_id_type=member_id_type,
                perm=permission,
            )

    def list_members(
        self,
        token: str,
        *,
        resource_type: str | DriveResourceType,
        fields: Optional[str] = None,
        perm_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "type": _resource_type(resource_type),
                "fields": fields,
                "perm_type": perm_type,
            }
        )
        response = self._client.request_json(
            "GET",
            f"/drive/v1/permissions/{token}/members",
            params=params,
        )
        return _unwrap_data(response)

    def add_member(
        self,
        token: str,
        *,
        resource_type: str | DriveResourceType,
        member_id: str,
        perm: str,
        member_id_type: str = MemberIdType.OPEN_ID.value,
        member_kind: str = "user",
        need_notification: Optional[bool] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "type": _resource_type(resource_type),
                "need_notification": need_notification,
            }
        )
        response = self._client.request_json(
            "POST",
            f"/drive/v1/permissions/{token}/members",
            params=params,
            payload={
                "member_id": member_id,
                "member_type": _member_type(member_id_type),
                "perm": perm,
                "type": member_kind,
            },
        )
        return _unwrap_data(response)

    def batch_add_members(
        self,
        token: str,
        *,
        resource_type: str | DriveResourceType,
        members: list[Mapping[str, object]],
        need_notification: Optional[bool] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "type": _resource_type(resource_type),
                "need_notification": need_notification,
            }
        )
        response = self._client.request_json(
            "POST",
            f"/drive/v1/permissions/{token}/members/batch_create",
            params=params,
            payload={"members": [dict(member) for member in members]},
        )
        return _unwrap_data(response)

    def update_member(
        self,
        token: str,
        member_id: str,
        *,
        resource_type: str | DriveResourceType,
        perm: str,
        member_id_type: str = MemberIdType.OPEN_ID.value,
        member_kind: str = "user",
        perm_type: Optional[str] = None,
        need_notification: Optional[bool] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "type": _resource_type(resource_type),
                "need_notification": need_notification,
            }
        )
        payload: dict[str, object] = {
            "member_type": _member_type(member_id_type),
            "perm": perm,
            "type": member_kind,
        }
        if perm_type is not None:
            payload["perm_type"] = perm_type
        response = self._client.request_json(
            "PUT",
            f"/drive/v1/permissions/{token}/members/{member_id}",
            params=params,
            payload=payload,
        )
        return _unwrap_data(response)

    def remove_member(
        self,
        token: str,
        member_id: str,
        *,
        resource_type: str | DriveResourceType,
        member_id_type: Optional[str] = None,
        perm_type: Optional[str] = None,
    ) -> None:
        params = _drop_none(
            {
                "type": _resource_type(resource_type),
                "member_type": _member_type(member_id_type) if member_id_type else None,
            }
        )
        payload = _drop_none({"perm_type": perm_type})
        self._client.request_json(
            "DELETE",
            f"/drive/v1/permissions/{token}/members/{member_id}",
            params=params,
            payload=payload if payload else None,
        )

    def check_member_permission(
        self,
        token: str,
        *,
        resource_type: str | DriveResourceType,
        action: str,
    ) -> Mapping[str, Any]:
        params = {
            "type": _resource_type(resource_type),
            "action": action,
        }
        response = self._client.request_json(
            "GET",
            f"/drive/v1/permissions/{token}/members/auth",
            params=params,
        )
        return _unwrap_data(response)

    def transfer_owner(
        self,
        token: str,
        *,
        resource_type: str | DriveResourceType,
        new_owner_id: str,
        new_owner_id_type: str = MemberIdType.OPEN_ID.value,
        need_notification: Optional[bool] = None,
        remove_old_owner: Optional[bool] = None,
        stay_put: Optional[bool] = None,
        old_owner_perm: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "type": _resource_type(resource_type),
                "need_notification": need_notification,
                "remove_old_owner": remove_old_owner,
                "stay_put": stay_put,
                "old_owner_perm": old_owner_perm,
            }
        )
        payload = {
            "member_id": new_owner_id,
            "member_type": _member_type(new_owner_id_type),
        }
        response = self._client.request_json(
            "POST",
            f"/drive/v1/permissions/{token}/members/transfer_owner",
            params=params,
            payload=payload,
        )
        return _unwrap_data(response)

    def get_public_settings(
        self,
        token: str,
        *,
        resource_type: str | DriveResourceType,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "GET",
            f"/drive/v2/permissions/{token}/public",
            params={"type": _resource_type(resource_type)},
        )
        return _unwrap_data(response)

    def update_public_settings(
        self,
        token: str,
        settings: Mapping[str, object],
        *,
        resource_type: str | DriveResourceType,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "PATCH",
            f"/drive/v2/permissions/{token}/public",
            params={"type": _resource_type(resource_type)},
            payload=dict(settings),
        )
        return _unwrap_data(response)

    def enable_password(
        self,
        token: str,
        *,
        resource_type: str | DriveResourceType,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            f"/drive/v1/permissions/{token}/public/password",
            params={"type": _resource_type(resource_type)},
        )
        return _unwrap_data(response)

    def refresh_password(
        self,
        token: str,
        *,
        resource_type: str | DriveResourceType,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "PUT",
            f"/drive/v1/permissions/{token}/public/password",
            params={"type": _resource_type(resource_type)},
        )
        return _unwrap_data(response)

    def disable_password(
        self,
        token: str,
        *,
        resource_type: str | DriveResourceType,
    ) -> None:
        self._client.request_json(
            "DELETE",
            f"/drive/v1/permissions/{token}/public/password",
            params={"type": _resource_type(resource_type)},
        )


class AsyncDrivePermissionService:
    def __init__(self, feishu_client: AsyncFeishuClient) -> None:
        self._client = feishu_client

    async def grant_edit_permission(
        self,
        token: str,
        member_id: str,
        member_id_type: str = MemberIdType.OPEN_ID.value,
        *,
        resource_type: str | DriveResourceType,
        permission: str,
    ) -> None:
        try:
            await self.add_member(
                token,
                resource_type=resource_type,
                member_id=member_id,
                member_id_type=member_id_type,
                perm=permission,
            )
            return
        except FeishuError:
            await self.update_member(
                token,
                member_id,
                resource_type=resource_type,
                member_id_type=member_id_type,
                perm=permission,
            )

    async def list_members(
        self,
        token: str,
        *,
        resource_type: str | DriveResourceType,
        fields: Optional[str] = None,
        perm_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "type": _resource_type(resource_type),
                "fields": fields,
                "perm_type": perm_type,
            }
        )
        response = await self._client.request_json(
            "GET",
            f"/drive/v1/permissions/{token}/members",
            params=params,
        )
        return _unwrap_data(response)

    async def add_member(
        self,
        token: str,
        *,
        resource_type: str | DriveResourceType,
        member_id: str,
        perm: str,
        member_id_type: str = MemberIdType.OPEN_ID.value,
        member_kind: str = "user",
        need_notification: Optional[bool] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "type": _resource_type(resource_type),
                "need_notification": need_notification,
            }
        )
        response = await self._client.request_json(
            "POST",
            f"/drive/v1/permissions/{token}/members",
            params=params,
            payload={
                "member_id": member_id,
                "member_type": _member_type(member_id_type),
                "perm": perm,
                "type": member_kind,
            },
        )
        return _unwrap_data(response)

    async def batch_add_members(
        self,
        token: str,
        *,
        resource_type: str | DriveResourceType,
        members: list[Mapping[str, object]],
        need_notification: Optional[bool] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "type": _resource_type(resource_type),
                "need_notification": need_notification,
            }
        )
        response = await self._client.request_json(
            "POST",
            f"/drive/v1/permissions/{token}/members/batch_create",
            params=params,
            payload={"members": [dict(member) for member in members]},
        )
        return _unwrap_data(response)

    async def update_member(
        self,
        token: str,
        member_id: str,
        *,
        resource_type: str | DriveResourceType,
        perm: str,
        member_id_type: str = MemberIdType.OPEN_ID.value,
        member_kind: str = "user",
        perm_type: Optional[str] = None,
        need_notification: Optional[bool] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "type": _resource_type(resource_type),
                "need_notification": need_notification,
            }
        )
        payload: dict[str, object] = {
            "member_type": _member_type(member_id_type),
            "perm": perm,
            "type": member_kind,
        }
        if perm_type is not None:
            payload["perm_type"] = perm_type
        response = await self._client.request_json(
            "PUT",
            f"/drive/v1/permissions/{token}/members/{member_id}",
            params=params,
            payload=payload,
        )
        return _unwrap_data(response)

    async def remove_member(
        self,
        token: str,
        member_id: str,
        *,
        resource_type: str | DriveResourceType,
        member_id_type: Optional[str] = None,
        perm_type: Optional[str] = None,
    ) -> None:
        params = _drop_none(
            {
                "type": _resource_type(resource_type),
                "member_type": _member_type(member_id_type) if member_id_type else None,
            }
        )
        payload = _drop_none({"perm_type": perm_type})
        await self._client.request_json(
            "DELETE",
            f"/drive/v1/permissions/{token}/members/{member_id}",
            params=params,
            payload=payload if payload else None,
        )

    async def check_member_permission(
        self,
        token: str,
        *,
        resource_type: str | DriveResourceType,
        action: str,
    ) -> Mapping[str, Any]:
        params = {
            "type": _resource_type(resource_type),
            "action": action,
        }
        response = await self._client.request_json(
            "GET",
            f"/drive/v1/permissions/{token}/members/auth",
            params=params,
        )
        return _unwrap_data(response)

    async def transfer_owner(
        self,
        token: str,
        *,
        resource_type: str | DriveResourceType,
        new_owner_id: str,
        new_owner_id_type: str = MemberIdType.OPEN_ID.value,
        need_notification: Optional[bool] = None,
        remove_old_owner: Optional[bool] = None,
        stay_put: Optional[bool] = None,
        old_owner_perm: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "type": _resource_type(resource_type),
                "need_notification": need_notification,
                "remove_old_owner": remove_old_owner,
                "stay_put": stay_put,
                "old_owner_perm": old_owner_perm,
            }
        )
        payload = {
            "member_id": new_owner_id,
            "member_type": _member_type(new_owner_id_type),
        }
        response = await self._client.request_json(
            "POST",
            f"/drive/v1/permissions/{token}/members/transfer_owner",
            params=params,
            payload=payload,
        )
        return _unwrap_data(response)

    async def get_public_settings(
        self,
        token: str,
        *,
        resource_type: str | DriveResourceType,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "GET",
            f"/drive/v2/permissions/{token}/public",
            params={"type": _resource_type(resource_type)},
        )
        return _unwrap_data(response)

    async def update_public_settings(
        self,
        token: str,
        settings: Mapping[str, object],
        *,
        resource_type: str | DriveResourceType,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "PATCH",
            f"/drive/v2/permissions/{token}/public",
            params={"type": _resource_type(resource_type)},
            payload=dict(settings),
        )
        return _unwrap_data(response)

    async def enable_password(
        self,
        token: str,
        *,
        resource_type: str | DriveResourceType,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/drive/v1/permissions/{token}/public/password",
            params={"type": _resource_type(resource_type)},
        )
        return _unwrap_data(response)

    async def refresh_password(
        self,
        token: str,
        *,
        resource_type: str | DriveResourceType,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "PUT",
            f"/drive/v1/permissions/{token}/public/password",
            params={"type": _resource_type(resource_type)},
        )
        return _unwrap_data(response)

    async def disable_password(
        self,
        token: str,
        *,
        resource_type: str | DriveResourceType,
    ) -> None:
        await self._client.request_json(
            "DELETE",
            f"/drive/v1/permissions/{token}/public/password",
            params={"type": _resource_type(resource_type)},
        )
