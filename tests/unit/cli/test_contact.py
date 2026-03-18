import json
from typing import Any
from feishu_bot_sdk import cli
from feishu_bot_sdk.contact import ContactService


def test_contact_user_batch_get(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    captured: dict[str, Any] = {}

    def _fake_batch_get_users(
        _self: ContactService,
        user_ids: list[str],
        *,
        user_id_type: str | None = None,
        department_id_type: str | None = None,
    ) -> dict[str, Any]:
        captured["user_ids"] = user_ids
        captured["user_id_type"] = user_id_type
        captured["department_id_type"] = department_id_type
        return {"items": [{"open_id": "ou_1"}, {"open_id": "ou_2"}]}

    monkeypatch.setattr(
        "feishu_bot_sdk.contact.ContactService.batch_get_users", _fake_batch_get_users
    )

    code = cli.main(
        [
            "contact",
            "user",
            "batch-get",
            "--user-id",
            "ou_1",
            "--user-id",
            "ou_2",
            "--user-id-type",
            "open_id",
            "--department-id-type",
            "open_department_id",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert captured["user_ids"] == ["ou_1", "ou_2"]
    assert captured["user_id_type"] == "open_id"
    assert captured["department_id_type"] == "open_department_id"
    payload = json.loads(capsys.readouterr().out)
    assert payload["items"][0]["open_id"] == "ou_1"


def test_contact_user_get_id_requires_email_or_mobile(
    monkeypatch: Any, capsys: Any
) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    code = cli.main(["contact", "user", "get-id", "--format", "json"])
    assert code == 2
    payload = json.loads(capsys.readouterr().out)
    assert "at least one of --email or --mobile is required" in payload["error"]


def test_contact_user_get_id(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    captured: dict[str, Any] = {}

    def _fake_batch_get_user_ids(
        _self: ContactService,
        *,
        emails: list[str] | None = None,
        mobiles: list[str] | None = None,
        include_resigned: bool | None = None,
        user_id_type: str | None = None,
    ) -> dict[str, Any]:
        captured["emails"] = emails
        captured["mobiles"] = mobiles
        captured["include_resigned"] = include_resigned
        captured["user_id_type"] = user_id_type
        return {"user_list": [{"open_id": "ou_1"}]}

    monkeypatch.setattr(
        "feishu_bot_sdk.contact.ContactService.batch_get_user_ids",
        _fake_batch_get_user_ids,
    )

    code = cli.main(
        [
            "contact",
            "user",
            "get-id",
            "--email",
            "a@example.com",
            "--mobile",
            "13800138000",
            "--include-resigned",
            "true",
            "--user-id-type",
            "open_id",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert captured["emails"] == ["a@example.com"]
    assert captured["mobiles"] == ["13800138000"]
    assert captured["include_resigned"] is True
    assert captured["user_id_type"] == "open_id"
    payload = json.loads(capsys.readouterr().out)
    assert payload["user_list"][0]["open_id"] == "ou_1"


def test_contact_department_children(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    captured: dict[str, Any] = {}

    def _fake_list_department_children(
        _self: ContactService,
        department_id: str,
        *,
        user_id_type: str | None = None,
        department_id_type: str | None = None,
        fetch_child: bool | None = None,
        page_size: int | None = None,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        captured["department_id"] = department_id
        captured["user_id_type"] = user_id_type
        captured["department_id_type"] = department_id_type
        captured["fetch_child"] = fetch_child
        captured["page_size"] = page_size
        captured["page_token"] = page_token
        return {"items": [{"department_id": "od_1"}], "has_more": False}

    monkeypatch.setattr(
        "feishu_bot_sdk.contact.ContactService.list_department_children",
        _fake_list_department_children,
    )

    code = cli.main(
        [
            "contact",
            "department",
            "children",
            "--department-id",
            "od_root",
            "--fetch-child",
            "true",
            "--page-size",
            "20",
            "--page-token",
            "next_1",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert captured["department_id"] == "od_root"
    assert captured["fetch_child"] is True
    assert captured["page_size"] == 20
    assert captured["page_token"] == "next_1"
    payload = json.loads(capsys.readouterr().out)
    assert payload["items"][0]["department_id"] == "od_1"


def test_contact_user_search_all(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    calls: list[str | None] = []

    def _fake_search_users(
        _self: ContactService,
        query: str,
        *,
        page_size: int | None = None,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        assert query == "Alice"
        calls.append(page_token)
        if page_token == "next_1":
            return {"users": [{"open_id": "ou_2"}], "has_more": False}
        return {"users": [{"open_id": "ou_1"}], "has_more": True, "page_token": "next_1"}

    monkeypatch.setattr(
        "feishu_bot_sdk.contact.ContactService.search_users", _fake_search_users
    )

    code = cli.main(
        ["contact", "user", "search", "--query", "Alice", "--all", "--format", "json"]
    )
    assert code == 0
    assert calls == [None, "next_1"]
    payload = json.loads(capsys.readouterr().out)
    assert payload["all"] is True
    assert payload["count"] == 2
    assert [item["open_id"] for item in payload["users"]] == ["ou_1", "ou_2"]


def test_contact_scope_get(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    captured: dict[str, Any] = {}

    def _fake_list_scopes(
        _self: ContactService,
        *,
        user_id_type: str | None = None,
        department_id_type: str | None = None,
        page_size: int | None = None,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        captured["user_id_type"] = user_id_type
        captured["department_id_type"] = department_id_type
        captured["page_size"] = page_size
        captured["page_token"] = page_token
        return {"user_ids": ["ou_1"], "department_ids": ["od_1"], "group_ids": ["g_1"]}

    monkeypatch.setattr(
        "feishu_bot_sdk.contact.ContactService.list_scopes", _fake_list_scopes
    )

    code = cli.main(
        [
            "contact",
            "scope",
            "get",
            "--user-id-type",
            "open_id",
            "--department-id-type",
            "open_department_id",
            "--page-size",
            "100",
            "--page-token",
            "scope_1",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert captured["user_id_type"] == "open_id"
    assert captured["department_id_type"] == "open_department_id"
    assert captured["page_size"] == 100
    assert captured["page_token"] == "scope_1"
    payload = json.loads(capsys.readouterr().out)
    assert payload["group_ids"] == ["g_1"]


def test_contact_scope_get_all(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    calls: list[str | None] = []

    def _fake_list_scopes(
        _self: ContactService,
        *,
        user_id_type: str | None = None,
        department_id_type: str | None = None,
        page_size: int | None = None,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        calls.append(page_token)
        if page_token == "next_1":
            return {
                "user_ids": ["ou_2"],
                "department_ids": ["od_2"],
                "group_ids": [],
                "has_more": False,
            }
        return {
            "user_ids": ["ou_1"],
            "department_ids": ["od_1"],
            "group_ids": ["g_1"],
            "has_more": True,
            "page_token": "next_1",
        }

    monkeypatch.setattr(
        "feishu_bot_sdk.contact.ContactService.list_scopes", _fake_list_scopes
    )

    code = cli.main(["contact", "scope", "get", "--all", "--format", "json"])
    assert code == 0
    assert calls == [None, "next_1"]
    payload = json.loads(capsys.readouterr().out)
    assert payload["all"] is True
    assert payload["count"] == 5
    assert payload["user_ids"] == ["ou_1", "ou_2"]
    assert payload["department_ids"] == ["od_1", "od_2"]
    assert payload["group_ids"] == ["g_1"]
