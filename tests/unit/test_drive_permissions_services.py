import asyncio
from typing import Any, Mapping, Optional, cast

from feishu_bot_sdk.drive_permissions import AsyncDrivePermissionService, DrivePermissionService
from feishu_bot_sdk.exceptions import FeishuError
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


def test_grant_edit_permission_fallback_to_update():
    def resolver(call: Mapping[str, Any]) -> Mapping[str, Any]:
        if call["method"] == "POST" and call["path"].endswith("/members"):
            raise FeishuError("already exists")
        return {"code": 0, "data": {"ok": True}}

    stub = _SyncClientStub(resolver)
    service = DrivePermissionService(cast(FeishuClient, stub))

    service.grant_edit_permission(
        "doc_1",
        "ou_1",
        "open_id",
        resource_type="docx",
        permission="edit",
    )

    assert len(stub.calls) == 2
    assert stub.calls[0]["method"] == "POST"
    assert stub.calls[0]["path"] == "/drive/v1/permissions/doc_1/members"
    assert stub.calls[1]["method"] == "PUT"
    assert stub.calls[1]["path"] == "/drive/v1/permissions/doc_1/members/ou_1"


def test_member_management_requests():
    def resolver(_call: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"code": 0, "data": {"ok": True}}

    stub = _SyncClientStub(resolver)
    service = DrivePermissionService(cast(FeishuClient, stub))

    service.add_member(
        "doc_1",
        resource_type="docx",
        member_id="ou_1",
        member_id_type="open_id",
        perm="edit",
        need_notification=True,
    )
    service.batch_add_members(
        "doc_1",
        resource_type="docx",
        members=[{"member_id": "ou_2", "member_type": "openid", "perm": "view", "type": "user"}],
    )
    service.list_members("doc_1", resource_type="docx", fields="member_id,perm")
    service.check_member_permission("doc_1", resource_type="docx", action="edit")
    service.transfer_owner("doc_1", resource_type="docx", new_owner_id="ou_3", remove_old_owner=True)
    service.remove_member(
        "doc_1",
        "ou_4",
        resource_type="docx",
        member_id_type="open_id",
        perm_type="container",
    )

    assert len(stub.calls) == 6
    assert stub.calls[0]["params"] == {"type": "docx", "need_notification": True}
    assert stub.calls[0]["payload"] == {
        "member_id": "ou_1",
        "member_type": "openid",
        "perm": "edit",
        "type": "user",
    }
    assert stub.calls[1]["path"] == "/drive/v1/permissions/doc_1/members/batch_create"
    assert stub.calls[2]["params"] == {"type": "docx", "fields": "member_id,perm"}
    assert stub.calls[3]["path"] == "/drive/v1/permissions/doc_1/members/auth"
    assert stub.calls[3]["params"] == {"type": "docx", "action": "edit"}
    assert stub.calls[4]["path"] == "/drive/v1/permissions/doc_1/members/transfer_owner"
    assert stub.calls[5]["method"] == "DELETE"
    assert stub.calls[5]["params"] == {"type": "docx", "member_type": "openid"}
    assert stub.calls[5]["payload"] == {"perm_type": "container"}


def test_public_and_password_requests():
    def resolver(_call: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"code": 0, "data": {"ok": True}}

    stub = _SyncClientStub(resolver)
    service = DrivePermissionService(cast(FeishuClient, stub))

    service.get_public_settings("doc_1", resource_type="docx")
    service.update_public_settings("doc_1", {"share_entity": "anyone_can_view"}, resource_type="docx")
    service.enable_password("doc_1", resource_type="docx")
    service.refresh_password("doc_1", resource_type="docx")
    service.disable_password("doc_1", resource_type="docx")

    assert len(stub.calls) == 5
    assert stub.calls[0]["path"] == "/drive/v2/permissions/doc_1/public"
    assert stub.calls[1]["method"] == "PATCH"
    assert stub.calls[1]["payload"] == {"share_entity": "anyone_can_view"}
    assert stub.calls[2]["path"] == "/drive/v1/permissions/doc_1/public/password"
    assert stub.calls[2]["method"] == "POST"
    assert stub.calls[4]["method"] == "DELETE"


def test_async_permission_service():
    def resolver(call: Mapping[str, Any]) -> Mapping[str, Any]:
        if call["method"] == "POST" and call["path"].endswith("/members"):
            raise FeishuError("already exists")
        return {"code": 0, "data": {"ok": True}}

    stub = _AsyncClientStub(resolver)
    service = AsyncDrivePermissionService(cast(AsyncFeishuClient, stub))

    async def run() -> None:
        await service.grant_edit_permission(
            "doc_1",
            "ou_1",
            "open_id",
            resource_type="docx",
            permission="edit",
        )
        await service.update_public_settings(
            "doc_1",
            {"share_entity": "tenant_editable"},
            resource_type="docx",
        )

    asyncio.run(run())

    assert len(stub.calls) == 3
    assert stub.calls[0]["method"] == "POST"
    assert stub.calls[1]["method"] == "PUT"
    assert stub.calls[2]["path"] == "/drive/v2/permissions/doc_1/public"
