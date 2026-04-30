from __future__ import annotations

import json
from typing import Any

import feishu_bot_sdk.cli as cli
from feishu_bot_sdk.feishu import FeishuClient


def test_contact_help_lists_lark_shortcuts(capsys: Any) -> None:
    code = cli.main(["contact", "--help"])

    assert code == 0
    output = capsys.readouterr().out
    assert "+get-user" in output
    assert "+search-user" in output


def test_contact_get_user_uses_bot_profile_endpoint(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")
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
                "user": {
                    "open_id": "ou_1",
                    "name": "Alice",
                    "email": "alice@example.com",
                }
            },
        }

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)

    code = cli.main(
        [
            "contact",
            "+get-user",
            "--as",
            "bot",
            "--user-id",
            "ou_1",
            "--user-id-type",
            "open_id",
            "--format",
            "json",
        ]
    )

    assert code == 0
    assert captured == {
        "method": "GET",
        "path": "/contact/v3/users/ou_1",
        "payload": None,
        "params": {"user_id_type": "open_id"},
    }
    payload = json.loads(capsys.readouterr().out)
    assert payload["user"]["open_id"] == "ou_1"
    assert payload["user"]["name"] == "Alice"


def test_contact_get_user_uses_current_user_endpoint_for_user_identity(
    monkeypatch: Any,
    capsys: Any,
) -> None:
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
        return {"code": 0, "data": {"open_id": "ou_self", "name": "Current User"}}

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)

    code = cli.main(
        [
            "contact",
            "+get-user",
            "--as",
            "user",
            "--user-access-token",
            "user_token",
            "--format",
            "json",
        ]
    )

    assert code == 0
    assert captured == {
        "method": "GET",
        "path": "/authen/v1/user_info",
        "payload": None,
        "params": None,
    }
    payload = json.loads(capsys.readouterr().out)
    assert payload["user"]["open_id"] == "ou_self"


def test_contact_search_user_builds_lark_search_payload(monkeypatch: Any, capsys: Any) -> None:
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
                "items": [
                    {
                        "id": "ou_alice",
                        "display_info": "<h>Alice</h>\nEngineering\n[Contacted 1 day ago]",
                        "meta_data": {
                            "i18n_names": {"en_us": "Alice"},
                            "mail_address": "alice@example.com",
                            "enterprise_mail_address": "alice@corp.example",
                            "is_registered": True,
                            "chat_id": "oc_1",
                            "is_cross_tenant": False,
                            "description": "signature",
                        },
                    }
                ],
                "has_more": False,
            },
        }

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)

    code = cli.main(
        [
            "contact",
            "+search-user",
            "--as",
            "user",
            "--user-access-token",
            "user_token",
            "--query",
            "Alice",
            "--has-chatted",
            "--exclude-external-users",
            "--page-size",
            "10",
            "--format",
            "json",
        ]
    )

    assert code == 0
    assert captured == {
        "method": "POST",
        "path": "/contact/v3/users/search",
        "payload": {
            "query": "Alice",
            "filter": {
                "has_contact": True,
                "exclude_outer_contact": True,
            },
        },
        "params": {"page_size": 10},
    }
    payload = json.loads(capsys.readouterr().out)
    assert payload["users"][0]["open_id"] == "ou_alice"
    assert payload["users"][0]["localized_name"] == "Alice"
    assert payload["users"][0]["department"] == "Engineering"


def test_contact_search_user_requires_at_least_one_filter(capsys: Any) -> None:
    code = cli.main(
        [
            "contact",
            "+search-user",
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
