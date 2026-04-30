from __future__ import annotations

import json
from typing import Any

import feishu_bot_sdk.cli as cli
from feishu_bot_sdk.feishu import FeishuClient


def test_wiki_help_lists_lark_shortcuts(capsys: Any) -> None:
    code = cli.main(["wiki", "--help"])

    assert code == 0
    output = capsys.readouterr().out
    assert "+move" in output
    assert "+node-create" in output
    assert "+delete-space" in output


def test_wiki_node_create_posts_to_resolved_space(monkeypatch: Any, capsys: Any) -> None:
    captured: dict[str, Any] = {}

    def _fake_request_json(
        _self: FeishuClient,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        captured.update({"method": method, "path": path, "payload": payload, "params": params})
        return {
            "code": 0,
            "data": {
                "node": {
                    "space_id": "sp_1",
                    "node_token": "wikcn_node",
                    "obj_token": "doccn_doc",
                    "obj_type": "docx",
                    "node_type": "origin",
                    "title": "Launch Notes",
                }
            },
        }

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)

    code = cli.main(
        [
            "wiki",
            "+node-create",
            "--as",
            "bot",
            "--app-id",
            "cli_app",
            "--app-secret",
            "cli_secret",
            "--space-id",
            "sp_1",
            "--title",
            "Launch Notes",
            "--obj-type",
            "docx",
            "--format",
            "json",
        ]
    )

    assert code == 0
    assert captured == {
        "method": "POST",
        "path": "/wiki/v2/spaces/sp_1/nodes",
        "payload": {
            "node_type": "origin",
            "obj_type": "docx",
            "title": "Launch Notes",
        },
        "params": None,
    }
    payload = json.loads(capsys.readouterr().out)
    assert payload["resolved_space_id"] == "sp_1"
    assert payload["node_token"] == "wikcn_node"


def test_wiki_move_node_resolves_source_space(monkeypatch: Any, capsys: Any) -> None:
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
        if path == "/wiki/v2/spaces/get_node":
            assert params is not None
            token = str(params["token"])
            space_id = "sp_target" if token == "wikcn_parent" else "sp_source"
            return {"code": 0, "data": {"node": {"space_id": space_id, "node_token": token}}}
        if path == "/wiki/v2/spaces/sp_source/nodes/wikcn_node/move":
            return {
                "code": 0,
                "data": {
                    "node": {
                        "space_id": "sp_target",
                        "node_token": "wikcn_node",
                        "parent_node_token": "wikcn_parent",
                        "obj_type": "docx",
                    }
                },
            }
        raise AssertionError(f"unexpected path: {path}")

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)

    code = cli.main(
        [
            "wiki",
            "+move",
            "--as",
            "bot",
            "--app-id",
            "cli_app",
            "--app-secret",
            "cli_secret",
            "--node-token",
            "wikcn_node",
            "--target-space-id",
            "sp_target",
            "--target-parent-token",
            "wikcn_parent",
            "--format",
            "json",
        ]
    )

    assert code == 0
    assert calls == [
        {
            "method": "GET",
            "path": "/wiki/v2/spaces/get_node",
            "payload": None,
            "params": {"token": "wikcn_node"},
        },
        {
            "method": "GET",
            "path": "/wiki/v2/spaces/get_node",
            "payload": None,
            "params": {"token": "wikcn_parent"},
        },
        {
            "method": "POST",
            "path": "/wiki/v2/spaces/sp_source/nodes/wikcn_node/move",
            "payload": {
                "target_parent_token": "wikcn_parent",
                "target_space_id": "sp_target",
            },
            "params": None,
        },
    ]
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "node"
    assert payload["source_space_id"] == "sp_source"
    assert payload["target_space_id"] == "sp_target"


def test_wiki_delete_space_requires_yes_before_request(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")
    called = False

    def _fake_request_json(
        _self: FeishuClient,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        nonlocal called
        called = True
        return {"code": 0, "data": {}}

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)

    code = cli.main(["wiki", "+delete-space", "--space-id", "sp_1", "--format", "json"])

    assert code == 2
    assert called is False
    payload = json.loads(capsys.readouterr().out)
    assert "requires --yes" in payload["error"]["message"]


def test_wiki_delete_space_executes_sync_delete_with_yes(monkeypatch: Any, capsys: Any) -> None:
    captured: dict[str, Any] = {}

    def _fake_request_json(
        _self: FeishuClient,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        captured.update({"method": method, "path": path, "payload": payload, "params": params})
        return {"code": 0, "data": {}}

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)

    code = cli.main(
        [
            "wiki",
            "+delete-space",
            "--as",
            "bot",
            "--app-id",
            "cli_app",
            "--app-secret",
            "cli_secret",
            "--space-id",
            "sp_1",
            "--yes",
            "--format",
            "json",
        ]
    )

    assert code == 0
    assert captured == {
        "method": "DELETE",
        "path": "/wiki/v2/spaces/sp_1",
        "payload": None,
        "params": None,
    }
    payload = json.loads(capsys.readouterr().out)
    assert payload["space_id"] == "sp_1"
    assert payload["ready"] is True
    assert payload["status"] == "success"
