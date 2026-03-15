import io
import json
from typing import Any
from feishu_bot_sdk import cli
from feishu_bot_sdk.chat import ChatService


def test_chat_list_all_with_api_sort_value(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    calls: list[str | None] = []

    def _fake_list_chats(
        _self: ChatService,
        *,
        user_id_type: str | None = None,
        sort_type: str | None = None,
        page_size: int | None = None,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        assert user_id_type == "open_id"
        assert sort_type == "ByCreateTimeAsc"
        calls.append(page_token)
        if page_token == "next_1":
            return {"items": [{"chat_id": "oc_2"}], "has_more": False}
        return {
            "items": [{"chat_id": "oc_1"}],
            "has_more": True,
            "page_token": "next_1",
        }

    monkeypatch.setattr("feishu_bot_sdk.chat.ChatService.list_chats", _fake_list_chats)

    code = cli.main(
        [
            "chat",
            "list",
            "--user-id-type",
            "open_id",
            "--sort-type",
            "ByCreateTimeAsc",
            "--all",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert calls == [None, "next_1"]
    payload = json.loads(capsys.readouterr().out)
    assert payload["all"] is True
    assert payload["count"] == 2
    assert [item["chat_id"] for item in payload["items"]] == ["oc_1", "oc_2"]


def test_group_alias_member_add_from_stdin(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")
    monkeypatch.setattr("sys.stdin", io.StringIO('["ou_1","ou_2"]'))

    captured: dict[str, Any] = {}

    def _fake_add_members(
        _self: ChatService,
        chat_id: str,
        member_ids: list[str],
        *,
        member_id_type: str | None = None,
        succeed_type: int | None = None,
    ) -> dict[str, Any]:
        captured["chat_id"] = chat_id
        captured["member_ids"] = member_ids
        captured["member_id_type"] = member_id_type
        captured["succeed_type"] = succeed_type
        return {"ok": True}

    monkeypatch.setattr(
        "feishu_bot_sdk.chat.ChatService.add_members", _fake_add_members
    )

    code = cli.main(
        [
            "group",
            "member",
            "add",
            "--chat-id",
            "oc_1",
            "--member-id-type",
            "open_id",
            "--member-ids-stdin",
            "--succeed-type",
            "1",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert captured["chat_id"] == "oc_1"
    assert captured["member_ids"] == ["ou_1", "ou_2"]
    assert captured["member_id_type"] == "open_id"
    assert captured["succeed_type"] == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True


def test_chat_moderation_update_from_flags_ok_payload(
    monkeypatch: Any, capsys: Any
) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    captured: dict[str, Any] = {}

    def _fake_update_moderation(
        _self: ChatService,
        chat_id: str,
        moderation: dict[str, Any],
        *,
        user_id_type: str | None = None,
    ) -> dict[str, Any]:
        captured["chat_id"] = chat_id
        captured["moderation"] = moderation
        captured["user_id_type"] = user_id_type
        return {"ok": True}

    monkeypatch.setattr(
        "feishu_bot_sdk.chat.ChatService.update_moderation", _fake_update_moderation
    )

    code = cli.main(
        [
            "chat",
            "moderation",
            "update",
            "--chat-id",
            "oc_1",
            "--user-id-type",
            "open_id",
            "--moderation-setting",
            "moderator_list",
            "--moderator-added-id",
            "ou_1",
            "--moderator-removed-id",
            "ou_2",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert captured["chat_id"] == "oc_1"
    assert captured["user_id_type"] == "open_id"
    assert captured["moderation"] == {
        "moderation_setting": "moderator_list",
        "moderator_added_list": ["ou_1"],
        "moderator_removed_list": ["ou_2"],
    }
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True


def test_chat_menu_update_item_requires_update_field_without_full_payload(
    monkeypatch: Any, capsys: Any
) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    code = cli.main(
        [
            "chat",
            "menu",
            "update-item",
            "--chat-id",
            "oc_1",
            "--menu-item-id",
            "menu_1",
            "--menu-item-json",
            '{"name":"Docs"}',
            "--format",
            "json",
        ]
    )
    assert code == 2
    payload = json.loads(capsys.readouterr().out)
    assert "requires at least one --update-field" in payload["error"]


def test_chat_announcement_batch_update_from_requests(
    monkeypatch: Any, capsys: Any
) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    captured: dict[str, Any] = {}

    def _fake_batch_update(
        _self: ChatService,
        chat_id: str,
        update_request: dict[str, Any],
        *,
        revision_id: int | None = None,
        client_token: str | None = None,
        user_id_type: str | None = None,
    ) -> dict[str, Any]:
        captured["chat_id"] = chat_id
        captured["update_request"] = update_request
        captured["revision_id"] = revision_id
        captured["client_token"] = client_token
        captured["user_id_type"] = user_id_type
        return {"revision_id": 3}

    monkeypatch.setattr(
        "feishu_bot_sdk.chat.ChatService.batch_update_announcement_blocks",
        _fake_batch_update,
    )

    code = cli.main(
        [
            "chat",
            "announcement",
            "batch-update",
            "--chat-id",
            "oc_1",
            "--requests-json",
            '[{"update_text_elements":{"block_id":"dox_1","elements":[]}}]',
            "--revision-id",
            "2",
            "--client-token",
            "token_1",
            "--user-id-type",
            "open_id",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert captured["chat_id"] == "oc_1"
    assert captured["update_request"] == {
        "requests": [{"update_text_elements": {"block_id": "dox_1", "elements": []}}]
    }
    assert captured["revision_id"] == 2
    assert captured["client_token"] == "token_1"
    assert captured["user_id_type"] == "open_id"
    payload = json.loads(capsys.readouterr().out)
    assert payload["revision_id"] == 3


def test_chat_top_notice_put_message_shortcut(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    captured: dict[str, Any] = {}

    def _fake_put_top_notice(
        _self: ChatService,
        chat_id: str,
        notice: dict[str, Any],
    ) -> dict[str, Any]:
        captured["chat_id"] = chat_id
        captured["notice"] = notice
        return {"ok": True}

    monkeypatch.setattr(
        "feishu_bot_sdk.chat.ChatService.put_top_notice", _fake_put_top_notice
    )

    code = cli.main(
        [
            "chat",
            "top-notice",
            "put",
            "--chat-id",
            "oc_1",
            "--message-id",
            "om_1",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert captured["chat_id"] == "oc_1"
    assert captured["notice"] == {
        "chat_top_notice": [{"action_type": "1", "message_id": "om_1"}]
    }
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True


def test_chat_list_all(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    calls: list[str | None] = []

    def _fake_list_chats(
        _self: ChatService,
        *,
        user_id_type: str | None = None,
        sort_type: str | None = None,
        page_size: int | None = None,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        assert user_id_type == "open_id"
        assert sort_type == "name"
        calls.append(page_token)
        if page_token == "next_1":
            return {"items": [{"chat_id": "oc_2"}], "has_more": False}
        return {
            "items": [{"chat_id": "oc_1"}],
            "has_more": True,
            "page_token": "next_1",
        }

    monkeypatch.setattr("feishu_bot_sdk.chat.ChatService.list_chats", _fake_list_chats)

    code = cli.main(
        [
            "chat",
            "list",
            "--user-id-type",
            "open_id",
            "--sort-type",
            "name",
            "--all",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert calls == [None, "next_1"]
    payload = json.loads(capsys.readouterr().out)
    assert payload["all"] is True
    assert payload["count"] == 2
    assert [item["chat_id"] for item in payload["items"]] == ["oc_1", "oc_2"]


def test_group_alias_member_add(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    captured: dict[str, Any] = {}

    def _fake_add_members(
        _self: ChatService,
        chat_id: str,
        member_ids: list[str],
        *,
        member_id_type: str | None = None,
        succeed_type: int | None = None,
    ) -> dict[str, Any]:
        captured["chat_id"] = chat_id
        captured["member_ids"] = member_ids
        captured["member_id_type"] = member_id_type
        captured["succeed_type"] = succeed_type
        return {"invalid_id_list": []}

    monkeypatch.setattr(
        "feishu_bot_sdk.chat.ChatService.add_members", _fake_add_members
    )

    code = cli.main(
        [
            "group",
            "member",
            "add",
            "--chat-id",
            "oc_1",
            "--member-id",
            "ou_1",
            "--member-id",
            "ou_2",
            "--member-id-type",
            "open_id",
            "--succeed-type",
            "1",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert captured["chat_id"] == "oc_1"
    assert captured["member_ids"] == ["ou_1", "ou_2"]
    assert captured["member_id_type"] == "open_id"
    assert captured["succeed_type"] == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["invalid_id_list"] == []


def test_chat_moderation_update_from_flags(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    captured: dict[str, Any] = {}

    def _fake_update_moderation(
        _self: ChatService,
        chat_id: str,
        moderation: dict[str, Any],
        *,
        user_id_type: str | None = None,
    ) -> dict[str, Any]:
        captured["chat_id"] = chat_id
        captured["moderation"] = moderation
        captured["user_id_type"] = user_id_type
        return {"moderation_setting": moderation.get("moderation_setting")}

    monkeypatch.setattr(
        "feishu_bot_sdk.chat.ChatService.update_moderation", _fake_update_moderation
    )

    code = cli.main(
        [
            "chat",
            "moderation",
            "update",
            "--chat-id",
            "oc_1",
            "--user-id-type",
            "open_id",
            "--moderation-setting",
            "moderator_list",
            "--moderator-added-id",
            "ou_1",
            "--moderator-removed-id",
            "ou_2",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert captured["chat_id"] == "oc_1"
    assert captured["user_id_type"] == "open_id"
    assert captured["moderation"] == {
        "moderation_setting": "moderator_list",
        "moderator_added_list": ["ou_1"],
        "moderator_removed_list": ["ou_2"],
    }
    payload = json.loads(capsys.readouterr().out)
    assert payload["moderation_setting"] == "moderator_list"


def test_chat_announcement_create_children_from_stdin(
    monkeypatch: Any, capsys: Any
) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(
            '[{"block_type":2,"text":{"elements":[{"text_run":{"content":"hello"}}]}}]'
        ),
    )

    captured: dict[str, Any] = {}

    def _fake_create_children(
        _self: ChatService,
        chat_id: str,
        block_id: str,
        children: list[dict[str, Any]],
        *,
        revision_id: int | None = None,
        client_token: str | None = None,
        user_id_type: str | None = None,
    ) -> dict[str, Any]:
        captured["chat_id"] = chat_id
        captured["block_id"] = block_id
        captured["children"] = children
        captured["revision_id"] = revision_id
        captured["client_token"] = client_token
        captured["user_id_type"] = user_id_type
        return {"children": [{"block_id": "blk_1"}], "client_token": client_token}

    monkeypatch.setattr(
        "feishu_bot_sdk.chat.ChatService.create_announcement_children",
        _fake_create_children,
    )

    code = cli.main(
        [
            "chat",
            "announcement",
            "create-children",
            "--chat-id",
            "oc_1",
            "--block-id",
            "oc_1",
            "--children-stdin",
            "--revision-id",
            "3",
            "--client-token",
            "idem_1",
            "--user-id-type",
            "open_id",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert captured["chat_id"] == "oc_1"
    assert captured["block_id"] == "oc_1"
    assert captured["revision_id"] == 3
    assert captured["client_token"] == "idem_1"
    assert captured["user_id_type"] == "open_id"
    assert captured["children"][0]["block_type"] == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["children"][0]["block_id"] == "blk_1"


def test_chat_menu_update_item_requires_update_field(
    monkeypatch: Any, capsys: Any
) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    code = cli.main(
        [
            "chat",
            "menu",
            "update-item",
            "--chat-id",
            "oc_1",
            "--menu-item-id",
            "menu_1",
            "--menu-item-json",
            '{"name":"Docs"}',
            "--format",
            "json",
        ]
    )
    assert code == 2
    captured = capsys.readouterr()
    assert "update-field" in (captured.out + captured.err)
