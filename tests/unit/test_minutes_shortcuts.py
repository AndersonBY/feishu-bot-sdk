from __future__ import annotations

import json
from typing import Any

import feishu_bot_sdk.cli as cli
from feishu_bot_sdk.feishu import FeishuClient


def test_minutes_help_lists_search_shortcut(capsys: Any) -> None:
    code = cli.main(["minutes", "--help"])

    assert code == 0
    output = capsys.readouterr().out
    assert "+search" in output
    assert "+download" in output


def test_minutes_search_builds_filter_payload(monkeypatch: Any, capsys: Any) -> None:
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
                "items": [{"token": "min_1", "display_info": "Weekly sync"}],
                "has_more": True,
                "page_token": "next_1",
                "total": 1,
            },
        }

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)

    code = cli.main(
        [
            "minutes",
            "+search",
            "--as",
            "user",
            "--user-access-token",
            "user_token",
            "--query",
            "Weekly",
            "--owner-ids",
            "ou_owner",
            "--participant-ids",
            "ou_a,ou_b",
            "--page-size",
            "10",
            "--page-token",
            "p1",
            "--format",
            "json",
        ]
    )

    assert code == 0
    assert captured == {
        "method": "POST",
        "path": "/minutes/v1/minutes/search",
        "payload": {
            "query": "Weekly",
            "filter": {
                "owner_ids": ["ou_owner"],
                "participant_ids": ["ou_a", "ou_b"],
            },
        },
        "params": {"page_size": 10, "page_token": "p1"},
    }
    payload = json.loads(capsys.readouterr().out)
    assert payload["items"][0]["token"] == "min_1"
    assert payload["has_more"] is True
    assert payload["page_token"] == "next_1"


def test_minutes_search_requires_a_filter(capsys: Any) -> None:
    code = cli.main(
        [
            "minutes",
            "+search",
            "--as",
            "user",
            "--user-access-token",
            "user_token",
            "--format",
            "json",
        ]
    )

    assert code == 2
    payload = json.loads(capsys.readouterr().out)
    assert "specify at least one" in payload["error"]["message"]
