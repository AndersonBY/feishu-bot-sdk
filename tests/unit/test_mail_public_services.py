import asyncio
from typing import Any, Mapping, Optional, cast

from feishu_bot_sdk.feishu import AsyncFeishuClient, FeishuClient
from feishu_bot_sdk.mail import (
    AsyncPublicMailboxAliasService,
    AsyncPublicMailboxMemberService,
    AsyncPublicMailboxService,
    PublicMailboxAliasService,
    PublicMailboxMemberService,
    PublicMailboxService,
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


def test_public_mailbox_request_shapes() -> None:
    def resolver(_call: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"code": 0, "data": {"ok": True}}

    stub = _SyncClientStub(resolver)
    mailbox = PublicMailboxService(cast(FeishuClient, stub))
    alias = PublicMailboxAliasService(cast(FeishuClient, stub))
    member = PublicMailboxMemberService(cast(FeishuClient, stub))

    mailbox.list_public_mailboxes(page_size=20, page_token="p_1")
    mailbox.get_public_mailbox("support@example.com")
    mailbox.create_public_mailbox({"email": "support@example.com"})
    mailbox.update_public_mailbox("support@example.com", {"name": "Support"})
    mailbox.replace_public_mailbox("support@example.com", {"name": "Support 2"})
    mailbox.remove_to_recycle_bin("support@example.com", {"to_mail_address": "archive@example.com"})
    mailbox.delete_public_mailbox("support@example.com")

    alias.list_aliases("support@example.com")
    alias.create_alias("support@example.com", {"email_alias": "help@example.com"})
    alias.delete_alias("support@example.com", "alias_1")

    member.list_members("support@example.com", user_id_type="open_id", page_size=50, page_token="m_1")
    member.get_member("support@example.com", "member_1", user_id_type="open_id")
    member.create_member("support@example.com", {"user_id": "ou_1"}, user_id_type="open_id")
    member.batch_create_members("support@example.com", [{"user_id": "ou_1"}], user_id_type="open_id")
    member.delete_member("support@example.com", "member_1", user_id_type="open_id")
    member.batch_delete_members("support@example.com", ["member_1", "member_2"], user_id_type="open_id")
    member.clear_members("support@example.com")

    assert stub.calls[0]["path"] == "/mail/v1/public_mailboxes"
    assert stub.calls[0]["params"] == {"page_size": 20, "page_token": "p_1"}
    assert stub.calls[5]["path"] == "/mail/v1/public_mailboxes/support@example.com/remove_to_recycle_bin"
    assert stub.calls[5]["payload"] == {"to_mail_address": "archive@example.com"}
    assert stub.calls[7]["path"] == "/mail/v1/public_mailboxes/support@example.com/aliases"
    assert stub.calls[10]["params"] == {"user_id_type": "open_id", "page_size": 50, "page_token": "m_1"}
    assert stub.calls[13]["payload"] == {"items": [{"user_id": "ou_1"}]}
    assert stub.calls[15]["payload"] == {"member_id_list": ["member_1", "member_2"]}
    assert stub.calls[16]["path"] == "/mail/v1/public_mailboxes/support@example.com/members/clear"


def test_async_public_mailbox_iterators() -> None:
    def resolver(call: Mapping[str, Any]) -> Mapping[str, Any]:
        path = str(call["path"])
        page_token = call["params"].get("page_token")
        if path == "/mail/v1/public_mailboxes":
            if page_token == "mailbox_2":
                return {"code": 0, "data": {"items": [{"public_mailbox_id": "pb_2"}], "has_more": False}}
            return {"code": 0, "data": {"items": [{"public_mailbox_id": "pb_1"}], "has_more": True, "page_token": "mailbox_2"}}
        if path == "/mail/v1/public_mailboxes/support@example.com/members":
            return {"code": 0, "data": {"items": [{"member_id": "m_1"}], "has_more": False}}
        return {"code": 0, "data": {"ok": True}}

    stub = _AsyncClientStub(resolver)
    mailbox = AsyncPublicMailboxService(cast(AsyncFeishuClient, stub))
    alias = AsyncPublicMailboxAliasService(cast(AsyncFeishuClient, stub))
    member = AsyncPublicMailboxMemberService(cast(AsyncFeishuClient, stub))

    async def run() -> None:
        await alias.create_alias("support@example.com", {"email_alias": "help@example.com"})
        mailboxes = [item async for item in mailbox.iter_public_mailboxes(page_size=1)]
        members = [item async for item in member.iter_members("support@example.com", page_size=10)]

        assert mailboxes == [{"public_mailbox_id": "pb_1"}, {"public_mailbox_id": "pb_2"}]
        assert members == [{"member_id": "m_1"}]

    asyncio.run(run())
    assert stub.calls[0]["path"] == "/mail/v1/public_mailboxes/support@example.com/aliases"
