import json
from typing import Any
from feishu_bot_sdk import cli
from feishu_bot_sdk.search import SearchService


def test_search_app(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")
    monkeypatch.setenv("FEISHU_USER_ACCESS_TOKEN", "u_cli_dummy")

    captured: dict[str, Any] = {}

    def _fake_search_apps(
        _self: SearchService,
        query: str,
        *,
        user_id_type: str | None = None,
        page_size: int | None = None,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        captured["query"] = query
        captured["user_id_type"] = user_id_type
        captured["page_size"] = page_size
        captured["page_token"] = page_token
        return {"items": ["cli_1"], "has_more": False}

    monkeypatch.setattr(
        "feishu_bot_sdk.search.SearchService.search_apps", _fake_search_apps
    )

    code = cli.main(
        [
            "search",
            "app",
            "--query",
            "calendar",
            "--user-id-type",
            "open_id",
            "--page-size",
            "10",
            "--page-token",
            "next_1",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert captured["query"] == "calendar"
    assert captured["user_id_type"] == "open_id"
    assert captured["page_size"] == 10
    assert captured["page_token"] == "next_1"
    payload = json.loads(capsys.readouterr().out)
    assert payload["items"] == ["cli_1"]


def test_search_app_all(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")
    monkeypatch.setenv("FEISHU_USER_ACCESS_TOKEN", "u_cli_dummy")

    calls: list[str | None] = []

    def _fake_search_apps(
        _self: SearchService,
        query: str,
        *,
        user_id_type: str | None = None,
        page_size: int | None = None,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        assert query == "calendar"
        calls.append(page_token)
        if page_token == "next_1":
            return {"items": ["cli_2"], "has_more": False}
        return {"items": ["cli_1"], "has_more": True, "page_token": "next_1"}

    monkeypatch.setattr(
        "feishu_bot_sdk.search.SearchService.search_apps", _fake_search_apps
    )

    code = cli.main(
        ["search", "app", "--query", "calendar", "--all", "--format", "json"]
    )
    assert code == 0
    assert calls == [None, "next_1"]
    payload = json.loads(capsys.readouterr().out)
    assert payload["all"] is True
    assert payload["count"] == 2
    assert payload["items"] == ["cli_1", "cli_2"]


def test_search_message(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")
    monkeypatch.setenv("FEISHU_USER_ACCESS_TOKEN", "u_cli_dummy")

    captured: dict[str, Any] = {}

    def _fake_search_messages(
        _self: SearchService,
        query: str,
        *,
        user_id_type: str | None = None,
        page_size: int | None = None,
        page_token: str | None = None,
        from_ids: list[str] | None = None,
        chat_ids: list[str] | None = None,
        message_type: str | None = None,
        at_chatter_ids: list[str] | None = None,
        from_type: str | None = None,
        chat_type: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> dict[str, Any]:
        captured["query"] = query
        captured["from_ids"] = from_ids
        captured["chat_ids"] = chat_ids
        captured["message_type"] = message_type
        captured["at_chatter_ids"] = at_chatter_ids
        captured["from_type"] = from_type
        captured["chat_type"] = chat_type
        captured["start_time"] = start_time
        captured["end_time"] = end_time
        return {"items": ["om_1"], "has_more": False}

    monkeypatch.setattr(
        "feishu_bot_sdk.search.SearchService.search_messages", _fake_search_messages
    )

    code = cli.main(
        [
            "search",
            "message",
            "--query",
            "incident",
            "--from-id",
            "ou_1",
            "--chat-id",
            "oc_1",
            "--message-type",
            "image",
            "--at-chatter-id",
            "ou_2",
            "--from-type",
            "user",
            "--chat-type",
            "group_chat",
            "--start-time",
            "1700000000",
            "--end-time",
            "1700003600",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert captured["query"] == "incident"
    assert captured["from_ids"] == ["ou_1"]
    assert captured["chat_ids"] == ["oc_1"]
    assert captured["message_type"] == "image"
    assert captured["at_chatter_ids"] == ["ou_2"]
    assert captured["from_type"] == "user"
    assert captured["chat_type"] == "group_chat"
    assert captured["start_time"] == "1700000000"
    assert captured["end_time"] == "1700003600"
    payload = json.loads(capsys.readouterr().out)
    assert payload["items"] == ["om_1"]


def test_search_doc_wiki(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")
    monkeypatch.setenv("FEISHU_USER_ACCESS_TOKEN", "u_cli_dummy")

    captured: dict[str, Any] = {}

    def _fake_search_doc_wiki(
        _self: SearchService,
        query: str,
        *,
        doc_filter: dict[str, Any] | None = None,
        wiki_filter: dict[str, Any] | None = None,
        page_token: str | None = None,
        page_size: int | None = None,
    ) -> dict[str, Any]:
        captured["query"] = query
        captured["doc_filter"] = doc_filter
        captured["wiki_filter"] = wiki_filter
        captured["page_token"] = page_token
        captured["page_size"] = page_size
        return {"res_units": [{"token": "doc_1"}], "has_more": False}

    monkeypatch.setattr(
        "feishu_bot_sdk.search.SearchService.search_doc_wiki", _fake_search_doc_wiki
    )

    code = cli.main(
        [
            "search",
            "doc-wiki",
            "--query",
            "weekly",
            "--doc-filter-json",
            '{"only_title": true}',
            "--wiki-filter-json",
            '{"space_ids": ["space_1"]}',
            "--page-size",
            "20",
            "--page-token",
            "next_1",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert captured["query"] == "weekly"
    assert captured["doc_filter"] == {"only_title": True}
    assert captured["wiki_filter"] == {"space_ids": ["space_1"]}
    assert captured["page_size"] == 20
    assert captured["page_token"] == "next_1"
    payload = json.loads(capsys.readouterr().out)
    assert payload["res_units"][0]["token"] == "doc_1"


def test_search_doc_wiki_requires_filter(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")
    monkeypatch.setenv("FEISHU_USER_ACCESS_TOKEN", "u_cli_dummy")

    code = cli.main(["search", "doc-wiki", "--query", "weekly", "--format", "json"])
    assert code == 2
    payload = json.loads(capsys.readouterr().out)
    assert "requires at least one of doc_filter or wiki_filter" in payload["error"]


def test_search_defaults_to_user_auth_even_when_env_tenant(
    monkeypatch: Any, capsys: Any
) -> None:
    monkeypatch.setenv("FEISHU_AUTH_MODE", "tenant")
    monkeypatch.setenv("FEISHU_USER_ACCESS_TOKEN", "u_cli_dummy")
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    def _fake_search_apps(
        _self: SearchService,
        query: str,
        *,
        user_id_type: str | None = None,
        page_size: int | None = None,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        return {"items": [query], "has_more": False}

    monkeypatch.setattr(
        "feishu_bot_sdk.search.SearchService.search_apps", _fake_search_apps
    )

    code = cli.main(["search", "app", "--query", "calendar", "--format", "json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["items"] == ["calendar"]
