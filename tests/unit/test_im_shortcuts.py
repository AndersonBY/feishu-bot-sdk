from __future__ import annotations

import json
from typing import Any

import feishu_bot_sdk.cli as cli
from feishu_bot_sdk.feishu import FeishuClient


def test_im_help_lists_lark_shortcuts(capsys: Any) -> None:
    code = cli.main(["im", "--help"])

    assert code == 0
    output = capsys.readouterr().out
    for command in (
        "+chat-create",
        "+chat-messages-list",
        "+chat-search",
        "+chat-update",
        "+messages-mget",
        "+messages-reply",
        "+messages-resources-download",
        "+messages-search",
        "+messages-send",
        "+threads-messages-list",
    ):
        assert command in output


def test_im_chat_create_builds_lark_payload(monkeypatch: Any, capsys: Any) -> None:
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
        if path == "/im/v1/chats":
            return {
                "code": 0,
                "data": {"chat_id": "oc_1", "name": "Release", "chat_type": "public", "owner_id": "ou_owner"},
            }
        if path == "/im/v1/chats/oc_1/link":
            return {"code": 0, "data": {"share_link": "https://example.com/share"}}
        raise AssertionError(f"unexpected path: {path}")

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)

    code = cli.main(
        [
            "im",
            "+chat-create",
            "--as",
            "bot",
            "--app-id",
            "cli_app",
            "--app-secret",
            "cli_secret",
            "--name",
            "Release",
            "--description",
            "Launch room",
            "--users",
            "ou_a,ou_b",
            "--bots",
            "cli_bot",
            "--owner",
            "ou_owner",
            "--type",
            "public",
            "--set-bot-manager",
            "--format",
            "json",
        ]
    )

    assert code == 0
    assert calls[0] == {
        "method": "POST",
        "path": "/im/v1/chats",
        "payload": {
            "chat_type": "public",
            "name": "Release",
            "description": "Launch room",
            "user_id_list": ["ou_a", "ou_b"],
            "bot_id_list": ["cli_bot"],
            "owner_id": "ou_owner",
        },
        "params": {"user_id_type": "open_id", "set_bot_manager": True},
    }
    payload = json.loads(capsys.readouterr().out)
    assert payload["chat_id"] == "oc_1"
    assert payload["share_link"] == "https://example.com/share"


def test_im_messages_send_and_reply_wrap_text(monkeypatch: Any, capsys: Any) -> None:
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
        return {"code": 0, "data": {"message_id": "om_reply", "chat_id": "oc_1", "create_time": "1710000000000"}}

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)

    send_code = cli.main(
        [
            "im",
            "+messages-send",
            "--as",
            "bot",
            "--app-id",
            "cli_app",
            "--app-secret",
            "cli_secret",
            "--chat-id",
            "oc_1",
            "--text",
            "hello <at id=ou_1>",
            "--idempotency-key",
            "dedupe-1",
            "--format",
            "json",
        ]
    )
    assert send_code == 0
    capsys.readouterr()

    reply_code = cli.main(
        [
            "im",
            "+messages-reply",
            "--as",
            "bot",
            "--app-id",
            "cli_app",
            "--app-secret",
            "cli_secret",
            "--message-id",
            "om_1",
            "--text",
            "reply",
            "--reply-in-thread",
            "--format",
            "json",
        ]
    )

    assert reply_code == 0
    assert calls[0] == {
        "method": "POST",
        "path": "/im/v1/messages",
        "payload": {
            "receive_id": "oc_1",
            "msg_type": "text",
            "content": '{"text": "hello <at user_id=\\"ou_1\\">"}',
            "uuid": "dedupe-1",
        },
        "params": {"receive_id_type": "chat_id"},
    }
    assert calls[1] == {
        "method": "POST",
        "path": "/im/v1/messages/om_1/reply",
        "payload": {
            "msg_type": "text",
            "content": '{"text": "reply"}',
            "reply_in_thread": True,
        },
        "params": None,
    }


def test_im_messages_mget_and_thread_list(monkeypatch: Any, capsys: Any) -> None:
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
        return {
            "code": 0,
            "data": {"items": [{"message_id": "om_1", "msg_type": "text", "content": "{}"}], "has_more": False},
        }

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)

    assert (
        cli.main(
            [
                "im",
                "+messages-mget",
                "--as",
                "bot",
                "--app-id",
                "cli_app",
                "--app-secret",
                "cli_secret",
                "--message-ids",
                "om_1,om_2",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert (
        cli.main(
            [
                "im",
                "+threads-messages-list",
                "--as",
                "bot",
                "--app-id",
                "cli_app",
                "--app-secret",
                "cli_secret",
                "--thread",
                "omt_1",
                "--sort",
                "desc",
                "--page-size",
                "25",
                "--format",
                "json",
            ]
        )
        == 0
    )

    assert calls[0] == {
        "method": "GET",
        "path": "/im/v1/messages/mget",
        "payload": None,
        "params": {"card_msg_content_type": "raw_card_content", "message_ids": ["om_1", "om_2"]},
    }
    assert calls[1] == {
        "method": "GET",
        "path": "/im/v1/messages",
        "payload": None,
        "params": {
            "container_id_type": "thread",
            "container_id": "omt_1",
            "sort_type": "ByCreateTimeDesc",
            "page_size": 25,
            "card_msg_content_type": "raw_card_content",
        },
    }


def test_im_search_commands_build_filters(monkeypatch: Any, capsys: Any) -> None:
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
        if path == "/im/v2/chats/search":
            return {
                "code": 0,
                "data": {"items": [{"meta_data": {"chat_id": "oc_1", "name": "Release"}}], "total": 1},
            }
        if path == "/im/v1/messages/search":
            return {"code": 0, "data": {"items": [{"meta_data": {"message_id": "om_1"}}], "has_more": False}}
        if path == "/im/v1/messages/mget":
            return {"code": 0, "data": {"items": [{"message_id": "om_1", "chat_id": "oc_1"}]}}
        if path == "/im/v1/chats/batch_query":
            return {"code": 0, "data": {"items": [{"chat_id": "oc_1", "name": "Release", "chat_mode": "group"}]}}
        raise AssertionError(f"unexpected path: {path}")

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)

    assert (
        cli.main(
            [
                "im",
                "+chat-search",
                "--as",
                "bot",
                "--app-id",
                "cli_app",
                "--app-secret",
                "cli_secret",
                "--query",
                "release-room",
                "--member-ids",
                "ou_1",
                "--search-types",
                "private,public_joined",
                "--sort-by",
                "update_time_desc",
                "--page-size",
                "10",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert (
        cli.main(
            [
                "im",
                "+messages-search",
                "--as",
                "user",
                "--user-access-token",
                "user_token",
                "--query",
                "release",
                "--chat-id",
                "oc_1",
                "--sender",
                "ou_1",
                "--is-at-me",
                "--at-chatter-ids",
                "ou_2",
                "--page-size",
                "10",
                "--format",
                "json",
            ]
        )
        == 0
    )

    assert calls[0] == {
        "method": "POST",
        "path": "/im/v2/chats/search",
        "payload": {
            "query": '"release-room"',
            "filter": {
                "search_types": ["private", "public_joined"],
                "member_ids": ["ou_1"],
            },
            "sorter": "update_time_desc",
        },
        "params": {"page_size": 10},
    }
    assert calls[1] == {
        "method": "POST",
        "path": "/im/v1/messages/search",
        "payload": {
            "query": "release",
            "filter": {
                "chat_ids": ["oc_1"],
                "from_ids": ["ou_1"],
                "is_at_me": True,
                "at_chatter_ids": ["ou_2"],
            },
        },
        "params": {"page_size": 10},
    }


def test_im_chat_update_and_resource_download(monkeypatch: Any, tmp_path: Any, capsys: Any) -> None:
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
        return {"code": 0, "data": {}}

    class _FakeResponse:
        status_code = 200
        content = b"file-bytes"
        text = ""
        headers = {"content-type": "text/plain", "content-disposition": 'attachment; filename="note.txt"'}

        def raise_for_status(self) -> None:
            return None

    class _FakeClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            return None

        def __enter__(self) -> "_FakeClient":
            return self

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
            return False

        def get(self, url: str, headers: dict[str, str] | None = None) -> _FakeResponse:
            assert "im/v1/messages/om_1/resources/file_1" in url
            return _FakeResponse()

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)
    monkeypatch.setattr("feishu_bot_sdk.cli.commands.im_shortcuts.httpx.Client", _FakeClient)

    assert (
        cli.main(
            [
                "im",
                "+chat-update",
                "--as",
                "bot",
                "--app-id",
                "cli_app",
                "--app-secret",
                "cli_secret",
                "--chat-id",
                "oc_1",
                "--name",
                "New name",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()

    output_dir = tmp_path / "downloads"
    output_dir.mkdir()
    assert (
        cli.main(
            [
                "im",
                "+messages-resources-download",
                "--as",
                "bot",
                "--access-token",
                "tenant_token",
                "--message-id",
                "om_1",
                "--file-key",
                "file_1",
                "--type",
                "file",
                "--output",
                str(output_dir),
                "--format",
                "json",
            ]
        )
        == 0
    )

    assert calls[0] == {
        "method": "PUT",
        "path": "/im/v1/chats/oc_1",
        "payload": {"name": "New name"},
        "params": {"user_id_type": "open_id"},
    }
    payload = json.loads(capsys.readouterr().out)
    assert payload["size_bytes"] == len(b"file-bytes")
    assert (output_dir / "note.txt").read_bytes() == b"file-bytes"


def test_im_resource_download_http_error_is_not_internal_error(monkeypatch: Any, tmp_path: Any, capsys: Any) -> None:
    class _FakeResponse:
        status_code = 400
        content = b"bad request"
        text = '{"code":99992354,"msg":"invalid message"}'
        headers = {"content-type": "application/json"}

    class _FakeClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            return None

        def __enter__(self) -> "_FakeClient":
            return self

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
            return False

        def get(self, url: str, headers: dict[str, str] | None = None) -> _FakeResponse:
            assert "im/v1/messages/missing/resources/file_1" in url
            return _FakeResponse()

    monkeypatch.setattr("feishu_bot_sdk.cli.commands.im_shortcuts.httpx.Client", _FakeClient)

    code = cli.main(
        [
            "im",
            "+messages-resources-download",
            "--as",
            "bot",
            "--access-token",
            "tenant_token",
            "--message-id",
            "missing",
            "--file-key",
            "file_1",
            "--output",
            str(tmp_path),
            "--format",
            "json",
        ]
    )

    assert code == 4
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"]["type"] == "http_error"
    assert payload["error"]["code"] == 99992354
