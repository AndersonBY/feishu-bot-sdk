import asyncio
from typing import Any, Mapping, Optional, cast

from feishu_bot_sdk.feishu import AsyncFeishuClient, FeishuClient
from feishu_bot_sdk.mail import (
    AsyncMailGroupAliasService,
    AsyncMailGroupManagerService,
    AsyncMailGroupMemberService,
    AsyncMailGroupPermissionMemberService,
    AsyncMailGroupService,
    MailGroupAliasService,
    MailGroupManagerService,
    MailGroupMemberService,
    MailGroupPermissionMemberService,
    MailGroupService,
)


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


def test_mail_group_request_shapes() -> None:
    def resolver(_call: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"code": 0, "data": {"ok": True}}

    stub = _SyncClientStub(resolver)
    group = MailGroupService(cast(FeishuClient, stub))
    alias = MailGroupAliasService(cast(FeishuClient, stub))
    member = MailGroupMemberService(cast(FeishuClient, stub))
    permission = MailGroupPermissionMemberService(cast(FeishuClient, stub))
    manager = MailGroupManagerService(cast(FeishuClient, stub))

    group.list_mailgroups(page_size=20, page_token="g_1")
    group.get_mailgroup("group@example.com")
    group.create_mailgroup({"email": "group@example.com"})
    group.update_mailgroup("group@example.com", {"name": "Ops"})
    group.replace_mailgroup("group@example.com", {"name": "Ops 2"})
    group.delete_mailgroup("group@example.com")

    alias.list_aliases("group@example.com")
    alias.create_alias("group@example.com", {"email_alias": "alias@example.com"})
    alias.delete_alias("group@example.com", "alias_1")

    member.list_members("group@example.com", user_id_type="open_id", department_id_type="department_id", page_size=50, page_token="m_1")
    member.get_member("group@example.com", "member_1", user_id_type="open_id", department_id_type="department_id")
    member.create_member("group@example.com", {"user_id": "ou_1"}, user_id_type="open_id", department_id_type="department_id")
    member.batch_create_members("group@example.com", [{"user_id": "ou_1"}], user_id_type="open_id", department_id_type="department_id")
    member.delete_member("group@example.com", "member_1", user_id_type="open_id", department_id_type="department_id")
    member.batch_delete_members("group@example.com", ["member_1", "member_2"], user_id_type="open_id", department_id_type="department_id")

    permission.list_permission_members("group@example.com", user_id_type="open_id", department_id_type="department_id", page_size=50, page_token="p_1")
    permission.get_permission_member("group@example.com", "perm_1", user_id_type="open_id", department_id_type="department_id")
    permission.create_permission_member("group@example.com", {"user_id": "ou_1"}, user_id_type="open_id", department_id_type="department_id")
    permission.batch_create_permission_members("group@example.com", [{"user_id": "ou_1"}], user_id_type="open_id", department_id_type="department_id")
    permission.delete_permission_member("group@example.com", "perm_1", user_id_type="open_id", department_id_type="department_id")
    permission.batch_delete_permission_members("group@example.com", ["perm_1"], user_id_type="open_id", department_id_type="department_id")

    manager.list_managers("group@example.com", user_id_type="open_id", page_size=50, page_token="mgr_1")
    manager.batch_create_managers("group@example.com", [{"user_id": "ou_mgr"}], user_id_type="open_id")
    manager.batch_delete_managers("group@example.com", [{"user_id": "ou_mgr"}], user_id_type="open_id")

    assert stub.calls[0]["path"] == "/mail/v1/mailgroups"
    assert stub.calls[0]["params"] == {"page_size": 20, "page_token": "g_1"}
    assert stub.calls[2]["payload"] == {"email": "group@example.com"}
    assert stub.calls[6]["path"] == "/mail/v1/mailgroups/group@example.com/aliases"
    assert stub.calls[9]["params"] == {
        "user_id_type": "open_id",
        "department_id_type": "department_id",
        "page_size": 50,
        "page_token": "m_1",
    }
    assert stub.calls[12]["payload"] == {"items": [{"user_id": "ou_1"}]}
    assert stub.calls[14]["payload"] == {"member_id_list": ["member_1", "member_2"]}
    assert stub.calls[15]["path"] == "/mail/v1/mailgroups/group@example.com/permission_members"
    assert stub.calls[18]["payload"] == {"items": [{"user_id": "ou_1"}]}
    assert stub.calls[20]["payload"] == {"member_id_list": ["perm_1"]}
    assert stub.calls[21]["path"] == "/mail/v1/mailgroups/group@example.com/managers"
    assert stub.calls[22]["payload"] == {"mailgroup_manager_list": [{"user_id": "ou_mgr"}]}


def test_async_mail_group_iterators() -> None:
    def resolver(call: Mapping[str, Any]) -> Mapping[str, Any]:
        path = str(call["path"])
        page_token = call["params"].get("page_token")
        if path == "/mail/v1/mailgroups":
            if page_token == "group_2":
                return {"code": 0, "data": {"items": [{"mailgroup_id": "g_2"}], "has_more": False}}
            return {"code": 0, "data": {"items": [{"mailgroup_id": "g_1"}], "has_more": True, "page_token": "group_2"}}
        if path == "/mail/v1/mailgroups/group@example.com/members":
            return {"code": 0, "data": {"items": [{"member_id": "m_1"}], "has_more": False}}
        if path == "/mail/v1/mailgroups/group@example.com/permission_members":
            return {"code": 0, "data": {"items": [{"member_id": "p_1"}], "has_more": False}}
        if path == "/mail/v1/mailgroups/group@example.com/managers":
            return {"code": 0, "data": {"items": [{"user_id": "ou_mgr"}], "has_more": False}}
        return {"code": 0, "data": {"ok": True}}

    stub = _AsyncClientStub(resolver)
    group = AsyncMailGroupService(cast(AsyncFeishuClient, stub))
    alias = AsyncMailGroupAliasService(cast(AsyncFeishuClient, stub))
    member = AsyncMailGroupMemberService(cast(AsyncFeishuClient, stub))
    permission = AsyncMailGroupPermissionMemberService(cast(AsyncFeishuClient, stub))
    manager = AsyncMailGroupManagerService(cast(AsyncFeishuClient, stub))

    async def run() -> None:
        await alias.create_alias("group@example.com", {"email_alias": "alias@example.com"})
        groups = [item async for item in group.iter_mailgroups(page_size=1)]
        members = [item async for item in member.iter_members("group@example.com", page_size=10)]
        permissions = [item async for item in permission.iter_permission_members("group@example.com", page_size=10)]
        managers = [item async for item in manager.iter_managers("group@example.com", page_size=10)]

        assert groups == [{"mailgroup_id": "g_1"}, {"mailgroup_id": "g_2"}]
        assert members == [{"member_id": "m_1"}]
        assert permissions == [{"member_id": "p_1"}]
        assert managers == [{"user_id": "ou_mgr"}]

    asyncio.run(run())
    assert stub.calls[0]["path"] == "/mail/v1/mailgroups/group@example.com/aliases"
