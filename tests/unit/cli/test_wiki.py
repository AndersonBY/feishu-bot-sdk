import json
from typing import Any
from feishu_bot_sdk import cli
from feishu_bot_sdk.wiki import WikiService


def test_wiki_search_nodes(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    def _fake_search_nodes(
        _self: WikiService,
        query: str,
        *,
        space_id: str | None = None,
        node_id: str | None = None,
        page_size: int | None = None,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        return {
            "items": [{"title": "node-1", "query": query}],
            "space_id": space_id,
            "node_id": node_id,
            "page_size": page_size,
            "page_token": page_token,
        }

    monkeypatch.setattr(
        "feishu_bot_sdk.wiki.WikiService.search_nodes", _fake_search_nodes
    )

    code = cli.main(
        [
            "wiki",
            "search-nodes",
            "--query",
            "weekly",
            "--space-id",
            "sp_1",
            "--page-size",
            "10",
            "--format",
            "json",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["space_id"] == "sp_1"
    assert payload["page_size"] == 10
    assert payload["items"][0]["query"] == "weekly"


def test_wiki_list_spaces_all(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    calls: list[str | None] = []

    def _fake_list_spaces(
        _self: WikiService,
        *,
        page_size: int | None = None,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        calls.append(page_token)
        if page_token == "next_1":
            return {"items": [{"space_id": "sp_2"}], "has_more": False}
        return {
            "items": [{"space_id": "sp_1"}],
            "has_more": True,
            "page_token": "next_1",
        }

    monkeypatch.setattr(
        "feishu_bot_sdk.wiki.WikiService.list_spaces", _fake_list_spaces
    )

    code = cli.main(["wiki", "list-spaces", "--all", "--format", "json"])
    assert code == 0
    assert calls == [None, "next_1"]
    payload = json.loads(capsys.readouterr().out)
    assert payload["all"] is True
    assert payload["count"] == 2
    assert [item["space_id"] for item in payload["items"]] == ["sp_1", "sp_2"]


def test_wiki_search_nodes_all(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    calls: list[str | None] = []

    def _fake_search_nodes(
        _self: WikiService,
        query: str,
        *,
        space_id: str | None = None,
        node_id: str | None = None,
        page_size: int | None = None,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        assert query == "weekly"
        assert space_id == "sp_1"
        calls.append(page_token)
        if page_token == "next_1":
            return {"items": [{"title": "node-2"}], "has_more": False}
        return {
            "items": [{"title": "node-1"}],
            "has_more": True,
            "page_token": "next_1",
        }

    monkeypatch.setattr(
        "feishu_bot_sdk.wiki.WikiService.search_nodes", _fake_search_nodes
    )

    code = cli.main(
        [
            "wiki",
            "search-nodes",
            "--query",
            "weekly",
            "--space-id",
            "sp_1",
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
    assert [item["title"] for item in payload["items"]] == ["node-1", "node-2"]


def test_wiki_list_nodes_all(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    calls: list[str | None] = []

    def _fake_list_nodes(
        _self: WikiService,
        space_id: str,
        *,
        parent_node_token: str | None = None,
        page_size: int | None = None,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        assert space_id == "sp_1"
        assert parent_node_token == "node_parent_1"
        calls.append(page_token)
        if page_token == "next_1":
            return {"items": [{"node_token": "node_2"}], "has_more": False}
        return {
            "items": [{"node_token": "node_1"}],
            "has_more": True,
            "page_token": "next_1",
        }

    monkeypatch.setattr("feishu_bot_sdk.wiki.WikiService.list_nodes", _fake_list_nodes)

    code = cli.main(
        [
            "wiki",
            "list-nodes",
            "--space-id",
            "sp_1",
            "--parent-node-token",
            "node_parent_1",
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
    assert [item["node_token"] for item in payload["items"]] == ["node_1", "node_2"]
