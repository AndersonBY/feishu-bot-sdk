import asyncio
from pathlib import Path
from typing import Any, Mapping, Optional, cast

from feishu_bot_sdk.feishu import AsyncFeishuClient, FeishuClient
from feishu_bot_sdk.mail import (
    AsyncMailAddressService,
    AsyncMailContactService,
    AsyncMailEventService,
    AsyncMailFolderService,
    AsyncMailMailboxService,
    AsyncMailMessageService,
    AsyncMailRuleService,
    MailAddressService,
    MailContactService,
    MailEventService,
    MailFolderService,
    MailMailboxService,
    MailMessageService,
    MailRuleService,
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


def test_mail_user_request_shapes() -> None:
    def resolver(_call: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"code": 0, "data": {"ok": True}}

    stub = _SyncClientStub(resolver)
    mailbox = MailMailboxService(cast(FeishuClient, stub))
    message = MailMessageService(cast(FeishuClient, stub))
    folder = MailFolderService(cast(FeishuClient, stub))
    contact = MailContactService(cast(FeishuClient, stub))
    rule = MailRuleService(cast(FeishuClient, stub))
    event = MailEventService(cast(FeishuClient, stub))
    address = MailAddressService(cast(FeishuClient, stub))

    mailbox.list_aliases("me")
    mailbox.create_alias("me", "alias@example.com")
    mailbox.delete_alias("me", "alias_1")
    mailbox.delete_from_recycle_bin("user@example.com", transfer_mailbox="archive@example.com")

    message.list_messages("me", folder_id="INBOX", page_size=20, page_token="m_1", only_unread=True)
    message.get_message("me", "msg_1")
    message.get_by_card("me", card_id="card_1", owner_id="ou_1", user_id_type="open_id")
    message.send_message("me", {"subject": "Hello"})
    message.get_attachment_download_urls("me", "msg_1", ["att_1", "att_2"])

    folder.list_folders("me", folder_type=2)
    folder.create_folder("me", {"name": "Archive"})
    folder.update_folder("me", "folder_1", {"name": "Archive 2"})
    folder.delete_folder("me", "folder_1")

    contact.list_contacts("me", page_size=50, page_token="c_1")
    contact.create_contact("me", {"email": "alice@example.com"})
    contact.update_contact("me", "contact_1", {"name": "Alice"})
    contact.delete_contact("me", "contact_1")

    rule.list_rules("me", page_size=50, page_token="r_1")
    rule.create_rule("me", {"name": "Archive"})
    rule.update_rule("me", "rule_1", {"enabled": True})
    rule.delete_rule("me", "rule_1")
    rule.reorder_rules("me", ["rule_1", "rule_2"])

    event.get_subscription("me")
    event.subscribe("me", event_type=1)
    event.unsubscribe("me", event_type=1)
    address.query_status(["a@example.com", "b@example.com"])

    assert stub.calls[0]["path"] == "/mail/v1/user_mailboxes/me/aliases"
    assert stub.calls[1]["payload"] == {"email_alias": "alias@example.com"}
    assert stub.calls[2]["method"] == "DELETE"
    assert stub.calls[3]["path"] == "/mail/v1/user_mailboxes/user@example.com"
    assert stub.calls[3]["params"] == {"transfer_mailbox": "archive@example.com"}
    assert stub.calls[4]["params"] == {
        "folder_id": "INBOX",
        "page_size": 20,
        "page_token": "m_1",
        "only_unread": True,
    }
    assert stub.calls[6]["params"] == {
        "card_id": "card_1",
        "owner_id": "ou_1",
        "user_id_type": "open_id",
    }
    assert stub.calls[8]["params"] == {"attachment_ids": ["att_1", "att_2"]}
    assert stub.calls[9]["params"] == {"folder_type": 2}
    assert stub.calls[13]["path"] == "/mail/v1/user_mailboxes/me/mail_contacts"
    assert stub.calls[17]["path"] == "/mail/v1/user_mailboxes/me/rules"
    assert stub.calls[21]["payload"] == {"rule_ids": ["rule_1", "rule_2"]}
    assert stub.calls[22]["path"] == "/mail/v1/user_mailboxes/me/event/subscription"
    assert stub.calls[23]["payload"] == {"event_type": 1}
    assert stub.calls[25]["path"] == "/mail/v1/users/query"
    assert stub.calls[25]["payload"] == {"email_list": ["a@example.com", "b@example.com"]}


def test_mail_message_send_markdown_builds_rendered_payload(tmp_path: Path) -> None:
    image_path = tmp_path / "chart.png"
    image_path.write_bytes(b"image-bytes")

    stub = _SyncClientStub(lambda _call: {"code": 0, "data": {"message_id": "mail_1"}})
    message = MailMessageService(cast(FeishuClient, stub))

    message.send_markdown(
        "me",
        subject="Daily Report",
        to=["user@example.com", {"mail_address": "named@example.com", "name": "Named"}],
        cc=["cc@example.com"],
        markdown="# Report\n\n![Chart](chart.png)",
        dedupe_key="dedupe-1",
        head_from={"name": "Bot"},
        base_dir=tmp_path,
        latex_mode="raw",
    )

    assert len(stub.calls) == 1
    call = stub.calls[0]
    assert call["path"] == "/mail/v1/user_mailboxes/me/messages/send"
    assert call["payload"]["subject"] == "Daily Report"
    assert call["payload"]["to"] == [
        {"mail_address": "user@example.com"},
        {"mail_address": "named@example.com", "name": "Named"},
    ]
    assert call["payload"]["cc"] == [{"mail_address": "cc@example.com"}]
    assert call["payload"]["dedupe_key"] == "dedupe-1"
    assert call["payload"]["head_from"] == {"name": "Bot"}
    assert "cid:mail-inline-" in str(call["payload"]["body_html"])
    assert "Report" in str(call["payload"]["body_plain_text"])
    attachments = call["payload"]["attachments"]
    assert isinstance(attachments, list)
    assert attachments[0]["filename"] == "chart.png"
    assert attachments[0]["is_inline"] is True
    assert attachments[0]["cid"] in str(call["payload"]["body_html"])


def test_mail_message_send_markdown_inlines_remote_image(monkeypatch: Any) -> None:
    class _FakeResponse:
        headers = {"content-type": "image/png"}
        content = b"remote-bytes"

        def raise_for_status(self) -> None:
            return None

    monkeypatch.setattr(
        "feishu_bot_sdk.mail.rendering.httpx.get",
        lambda *_args, **_kwargs: _FakeResponse(),
    )

    stub = _SyncClientStub(lambda _call: {"code": 0, "data": {"message_id": "mail_remote_1"}})
    message = MailMessageService(cast(FeishuClient, stub))

    message.send_markdown(
        "me",
        subject="Remote Report",
        to=["user@example.com"],
        markdown="# Report\n\n![Chart](https://cdn.example.com/chart.png)",
        latex_mode="raw",
    )

    call = stub.calls[0]
    assert "cid:mail-inline-" in str(call["payload"]["body_html"])
    attachments = call["payload"]["attachments"]
    assert isinstance(attachments, list)
    assert attachments[0]["filename"] == "chart.png"
    assert attachments[0]["is_inline"] is True


def test_async_mail_user_iterators_and_calls() -> None:
    def resolver(call: Mapping[str, Any]) -> Mapping[str, Any]:
        path = str(call["path"])
        page_token = call["params"].get("page_token")
        if path == "/mail/v1/user_mailboxes/me/messages":
            if page_token == "msg_2":
                return {"code": 0, "data": {"items": ["msg_2"], "has_more": False}}
            return {"code": 0, "data": {"items": ["msg_1"], "has_more": True, "page_token": "msg_2"}}
        if path == "/mail/v1/user_mailboxes/me/folders":
            return {"code": 0, "data": {"items": [{"folder_id": "f_1"}, {"folder_id": "f_2"}]}}
        if path == "/mail/v1/user_mailboxes/me/mail_contacts":
            return {"code": 0, "data": {"items": [{"contact_id": "c_1"}], "has_more": False}}
        if path == "/mail/v1/user_mailboxes/me/rules":
            return {"code": 0, "data": {"items": [{"rule_id": "r_1"}], "has_more": False}}
        return {"code": 0, "data": {"ok": True}}

    stub = _AsyncClientStub(resolver)
    mailbox = AsyncMailMailboxService(cast(AsyncFeishuClient, stub))
    message = AsyncMailMessageService(cast(AsyncFeishuClient, stub))
    folder = AsyncMailFolderService(cast(AsyncFeishuClient, stub))
    contact = AsyncMailContactService(cast(AsyncFeishuClient, stub))
    rule = AsyncMailRuleService(cast(AsyncFeishuClient, stub))
    event = AsyncMailEventService(cast(AsyncFeishuClient, stub))
    address = AsyncMailAddressService(cast(AsyncFeishuClient, stub))

    async def run() -> None:
        await mailbox.create_alias("me", "alias@example.com")
        messages = [item async for item in message.iter_messages("me", folder_id="INBOX", page_size=1)]
        folders = [item async for item in folder.iter_folders("me", folder_type=2)]
        contacts = [item async for item in contact.iter_contacts("me", page_size=10)]
        rules = [item async for item in rule.iter_rules("me", page_size=10)]
        await event.subscribe("me", event_type=1)
        await address.query_status(["ops@example.com"])

        assert messages == ["msg_1", "msg_2"]
        assert folders == [{"folder_id": "f_1"}, {"folder_id": "f_2"}]
        assert contacts == [{"contact_id": "c_1"}]
        assert rules == [{"rule_id": "r_1"}]

    asyncio.run(run())
    assert stub.calls[0]["path"] == "/mail/v1/user_mailboxes/me/aliases"
    assert stub.calls[-2]["path"] == "/mail/v1/user_mailboxes/me/event/subscribe"
    assert stub.calls[-1]["payload"] == {"email_list": ["ops@example.com"]}


def test_async_mail_message_send_markdown_builds_rendered_payload(tmp_path: Path) -> None:
    image_path = tmp_path / "chart.png"
    image_path.write_bytes(b"image-bytes")

    stub = _AsyncClientStub(lambda _call: {"code": 0, "data": {"message_id": "mail_async_1"}})
    message = AsyncMailMessageService(cast(AsyncFeishuClient, stub))

    async def run() -> None:
        await message.send_markdown(
            "me",
            subject="Async Daily Report",
            to=["user@example.com"],
            markdown="# Async\n\n![Chart](chart.png)",
            base_dir=tmp_path,
            latex_mode="raw",
        )

    asyncio.run(run())
    assert len(stub.calls) == 1
    call = stub.calls[0]
    assert call["path"] == "/mail/v1/user_mailboxes/me/messages/send"
    assert call["payload"]["subject"] == "Async Daily Report"
    assert call["payload"]["to"] == [{"mail_address": "user@example.com"}]
    assert "cid:mail-inline-" in str(call["payload"]["body_html"])
    attachments = call["payload"]["attachments"]
    assert isinstance(attachments, list)
    assert attachments[0]["filename"] == "chart.png"
