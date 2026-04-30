from __future__ import annotations

import json
from typing import Any

import feishu_bot_sdk.cli as cli
from feishu_bot_sdk.feishu import FeishuClient


MAIL_P6_SHORTCUTS = (
    "+decline-receipt",
    "+forward",
    "+message",
    "+messages",
    "+reply",
    "+reply-all",
    "+send",
    "+send-receipt",
    "+share-to-chat",
    "+signature",
    "+template-create",
    "+template-update",
    "+triage",
    "+watch",
)


def _user_base() -> list[str]:
    return ["--as", "user", "--user-access-token", "user_token", "--format", "json"]


def test_mail_help_lists_p6_lark_shortcuts(capsys: Any) -> None:
    code = cli.main(["mail", "--help"])

    assert code == 0
    output = capsys.readouterr().out
    for shortcut in MAIL_P6_SHORTCUTS:
        assert shortcut in output


def test_mail_message_and_messages_shortcuts_build_read_requests(monkeypatch: Any, capsys: Any) -> None:
    calls: list[dict[str, Any]] = []

    def _fake_request_json(
        _self: FeishuClient,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        calls.append({"method": method, "path": path, "payload": payload, "params": params})
        return {"code": 0, "data": {"messages": [{"message_id": "msg_1"}], "message": {"message_id": "msg_1"}}}

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)

    assert cli.main(["mail", "+message", *_user_base(), "--mailbox", "me", "--message-id", "msg_1", "--html", "false"]) == 0
    capsys.readouterr()
    assert cli.main(["mail", "+messages", *_user_base(), "--mailbox", "me", "--message-ids", "msg_1,msg_2", "--html", "true"]) == 0

    assert calls[0] == {
        "method": "GET",
        "path": "/mail/v1/user_mailboxes/me/messages/msg_1",
        "payload": None,
        "params": {"format": "plain_text_full"},
    }
    assert calls[1] == {
        "method": "POST",
        "path": "/mail/v1/user_mailboxes/me/messages/batch_get",
        "payload": {"message_ids": ["msg_1", "msg_2"], "format": "full"},
        "params": None,
    }


def test_mail_send_reply_forward_shortcuts_create_or_send_drafts(monkeypatch: Any, capsys: Any) -> None:
    calls: list[dict[str, Any]] = []

    def _fake_request_json(
        _self: FeishuClient,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        calls.append({"method": method, "path": path, "payload": payload, "params": params})
        if path.endswith("/send"):
            return {"code": 0, "data": {"message_id": "sent_1"}}
        return {"code": 0, "data": {"draft": {"draft_id": "draft_1"}}}

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)

    assert cli.main(
        [
            "mail",
            "+send",
            *_user_base(),
            "--mailbox",
            "me",
            "--to",
            "a@example.com,b@example.com",
            "--cc",
            "c@example.com",
            "--subject",
            "Hello",
            "--body",
            "<b>Hi</b>",
            "--from",
            "sender@example.com",
        ]
    ) == 0
    capsys.readouterr()

    assert cli.main(
        [
            "mail",
            "+reply",
            *_user_base(),
            "--mailbox",
            "me",
            "--message-id",
            "msg_1",
            "--body",
            "Thanks",
            "--to",
            "extra@example.com",
            "--confirm-send",
        ]
    ) == 0
    capsys.readouterr()

    assert cli.main(
        [
            "mail",
            "+forward",
            *_user_base(),
            "--mailbox",
            "me",
            "--message-id",
            "msg_2",
            "--to",
            "next@example.com",
            "--body",
            "FYI",
        ]
    ) == 0

    assert calls[0] == {
        "method": "POST",
        "path": "/mail/v1/user_mailboxes/me/drafts",
        "payload": {
            "subject": "Hello",
            "body_html": "<b>Hi</b>",
            "to": [{"mail_address": "a@example.com"}, {"mail_address": "b@example.com"}],
            "cc": [{"mail_address": "c@example.com"}],
            "head_from": {"mail_address": "sender@example.com"},
        },
        "params": None,
    }
    assert calls[1]["path"] == "/mail/v1/user_mailboxes/me/drafts"
    assert calls[1]["payload"]["reply_to_message_id"] == "msg_1"
    assert calls[1]["payload"]["body_plain_text"] == "Thanks"
    assert calls[2] == {
        "method": "POST",
        "path": "/mail/v1/user_mailboxes/me/drafts/draft_1/send",
        "payload": {},
        "params": None,
    }
    assert calls[3]["path"] == "/mail/v1/user_mailboxes/me/drafts"
    assert calls[3]["payload"]["forward_message_id"] == "msg_2"
    assert calls[3]["payload"]["to"] == [{"mail_address": "next@example.com"}]


def test_mail_receipt_share_signature_and_template_shortcuts(monkeypatch: Any, capsys: Any) -> None:
    calls: list[dict[str, Any]] = []

    def _fake_request_json(
        _self: FeishuClient,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        calls.append({"method": method, "path": path, "payload": payload, "params": params})
        if path == "/mail/v1/user_mailboxes/me/messages/share_token":
            return {"code": 0, "data": {"card_id": "card_1"}}
        if path == "/mail/v1/user_mailboxes/me/share_tokens/card_1/send":
            return {"code": 0, "data": {"message_id": "im_1"}}
        if path == "/mail/v1/user_mailboxes/me/messages/msg_1":
            return {"code": 0, "data": {"message": {"message_id": "msg_1", "label_ids": ["READ_RECEIPT_REQUEST"]}}}
        if path == "/mail/v1/user_mailboxes/me/drafts":
            return {"code": 0, "data": {"draft": {"draft_id": "draft_1"}}}
        if path.endswith("/send"):
            return {"code": 0, "data": {"message_id": "sent_1"}}
        return {"code": 0, "data": {"ok": True, "template": {"id": "tpl_1"}}}

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)

    assert cli.main(["mail", "+decline-receipt", *_user_base(), "--mailbox", "me", "--message-id", "msg_1"]) == 0
    capsys.readouterr()
    assert cli.main(["mail", "+send-receipt", *_user_base(), "--mailbox", "me", "--message-id", "msg_1", "--from", "me@example.com"]) == 0
    capsys.readouterr()
    assert cli.main(["mail", "+share-to-chat", *_user_base(), "--mailbox", "me", "--message-id", "msg_1", "--receive-id", "oc_1"]) == 0
    capsys.readouterr()
    assert cli.main(["mail", "+signature", *_user_base(), "--from", "me"]) == 0
    capsys.readouterr()
    assert cli.main(
        [
            "mail",
            "+template-create",
            *_user_base(),
            "--mailbox",
            "me",
            "--name",
            "Daily",
            "--subject",
            "Subject",
            "--template-content",
            "<p>Hello</p>",
            "--to",
            "a@example.com",
        ]
    ) == 0
    capsys.readouterr()
    assert cli.main(
        [
            "mail",
            "+template-update",
            *_user_base(),
            "--mailbox",
            "me",
            "--template-id",
            "tpl_1",
            "--set-name",
            "Daily v2",
            "--set-subject",
            "Subject v2",
        ]
    ) == 0

    assert calls[0] == {
        "method": "PUT",
        "path": "/mail/v1/user_mailboxes/me/messages/msg_1/modify",
        "payload": {"remove_label_ids": ["READ_RECEIPT_REQUEST"]},
        "params": None,
    }
    assert calls[1] == {
        "method": "GET",
        "path": "/mail/v1/user_mailboxes/me/messages/msg_1",
        "payload": None,
        "params": {"format": "metadata"},
    }
    assert calls[2]["path"] == "/mail/v1/user_mailboxes/me/drafts"
    assert calls[2]["payload"]["read_receipt_message_id"] == "msg_1"
    assert calls[3]["path"] == "/mail/v1/user_mailboxes/me/drafts/draft_1/send"
    assert calls[4] == {
        "method": "POST",
        "path": "/mail/v1/user_mailboxes/me/messages/share_token",
        "payload": {"message_id": "msg_1"},
        "params": None,
    }
    assert calls[5] == {
        "method": "POST",
        "path": "/mail/v1/user_mailboxes/me/share_tokens/card_1/send",
        "payload": {"receive_id": "oc_1"},
        "params": {"receive_id_type": "chat_id"},
    }
    assert calls[6]["path"] == "/mail/v1/user_mailboxes/me/signatures"
    assert calls[7] == {
        "method": "POST",
        "path": "/mail/v1/user_mailboxes/me/templates",
        "payload": {
            "name": "Daily",
            "subject": "Subject",
            "template_content": "<p>Hello</p>",
            "tos": [{"mail_address": "a@example.com"}],
            "ccs": [],
            "bccs": [],
            "attachments": [],
            "is_plain_text_mode": False,
        },
        "params": None,
    }
    assert calls[8] == {
        "method": "PUT",
        "path": "/mail/v1/user_mailboxes/me/templates/tpl_1",
        "payload": {"name": "Daily v2", "subject": "Subject v2"},
        "params": None,
    }


def test_mail_triage_and_watch_shortcuts(monkeypatch: Any, capsys: Any) -> None:
    calls: list[dict[str, Any]] = []

    def _fake_request_json(
        _self: FeishuClient,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        calls.append({"method": method, "path": path, "payload": payload, "params": params})
        return {"code": 0, "data": {"items": [{"message_id": "msg_1"}], "has_more": False}}

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)

    assert cli.main(
        [
            "mail",
            "+triage",
            *_user_base(),
            "--mailbox",
            "me",
            "--query",
            "budget",
            "--filter",
            '{"folder":"INBOX","label_ids":["IMPORTANT"]}',
            "--max",
            "5",
            "--labels",
        ]
    ) == 0
    capsys.readouterr()
    assert cli.main(["mail", "+watch", *_user_base(), "--mailbox", "me", "--msg-format", "minimal"]) == 0
    watch_payload = json.loads(capsys.readouterr().out)

    assert calls[0] == {
        "method": "POST",
        "path": "/mail/v1/user_mailboxes/me/search",
        "payload": {
            "query": "budget",
            "filter": {"folder": "INBOX", "label_ids": ["IMPORTANT"]},
            "page_size": 5,
            "include_label_ids": True,
        },
        "params": None,
    }
    assert calls[1] == {
        "method": "POST",
        "path": "/mail/v1/user_mailboxes/me/event/subscribe",
        "payload": {"event_type": 1},
        "params": None,
    }
    assert watch_payload["watch"]["mailbox"] == "me"
    assert watch_payload["watch"]["msg_format"] == "minimal"
