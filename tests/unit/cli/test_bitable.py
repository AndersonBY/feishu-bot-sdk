import json
from typing import Any
from feishu_bot_sdk import cli
from feishu_bot_sdk.bitable import BitableService


def test_bitable_create_from_csv_with_grant(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    called: dict[str, Any] = {}

    def _fake_create_from_csv(
        _self: BitableService,
        csv_path: str,
        app_name: str,
        table_name: str,
    ) -> tuple[str, str]:
        called["csv_path"] = csv_path
        called["app_name"] = app_name
        called["table_name"] = table_name
        return "app_token_1", "https://example.com/base/app_token_1"

    def _fake_grant(
        _self: BitableService, app_token: str, member_id: str, member_id_type: str
    ) -> None:
        called["grant"] = (app_token, member_id, member_id_type)

    monkeypatch.setattr(
        "feishu_bot_sdk.bitable.BitableService.create_from_csv", _fake_create_from_csv
    )
    monkeypatch.setattr(
        "feishu_bot_sdk.bitable.BitableService.grant_edit_permission", _fake_grant
    )

    code = cli.main(
        [
            "bitable",
            "create-from-csv",
            "final.csv",
            "--app-name",
            "A",
            "--table-name",
            "T",
            "--grant-member-id",
            "ou_1",
        ]
    )
    assert code == 0
    assert called["csv_path"] == "final.csv"
    assert called["app_name"] == "A"
    assert called["table_name"] == "T"
    assert called["grant"] == ("app_token_1", "ou_1", "open_id")
    assert "app_token" in capsys.readouterr().out


def test_bitable_create_from_csv_with_grant_me_uses_current_user(
    monkeypatch: Any, capsys: Any
) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")
    monkeypatch.setenv("FEISHU_USER_ACCESS_TOKEN", "user_access_token_x")

    called: dict[str, Any] = {}

    def _fake_create_from_csv(
        _self: BitableService,
        csv_path: str,
        app_name: str,
        table_name: str,
    ) -> tuple[str, str]:
        called["csv_path"] = csv_path
        called["app_name"] = app_name
        called["table_name"] = table_name
        return "app_token_2", "https://example.com/base/app_token_2"

    def _fake_grant(
        _self: BitableService, app_token: str, member_id: str, member_id_type: str
    ) -> None:
        called["grant"] = (app_token, member_id, member_id_type)

    class _FakeUserInfo:
        open_id = "ou_current"
        user_id = "cli_user_current"
        union_id = "on_current"

    monkeypatch.setattr(
        "feishu_bot_sdk.bitable.BitableService.create_from_csv", _fake_create_from_csv
    )
    monkeypatch.setattr(
        "feishu_bot_sdk.bitable.BitableService.grant_edit_permission", _fake_grant
    )
    monkeypatch.setattr(
        "feishu_bot_sdk.feishu.FeishuClient.get_user_info",
        lambda _self, user_access_token=None: _FakeUserInfo(),
    )

    code = cli.main(
        [
            "bitable",
            "create-from-csv",
            "final.csv",
            "--app-name",
            "A",
            "--table-name",
            "T",
            "--grant-member-id",
            "me",
            "--member-id-type",
            "user_id",
            "--auth-mode",
            "user",
        ]
    )
    assert code == 0
    assert called["csv_path"] == "final.csv"
    assert called["grant"] == ("app_token_2", "cli_user_current", "user_id")
    assert "app_token" in capsys.readouterr().out


def test_bitable_grant_edit_me_uses_current_user(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")
    monkeypatch.setenv("FEISHU_USER_ACCESS_TOKEN", "user_access_token_x")

    called: dict[str, Any] = {}

    def _fake_grant(
        _self: BitableService, app_token: str, member_id: str, member_id_type: str
    ) -> None:
        called["grant"] = (app_token, member_id, member_id_type)

    class _FakeUserInfo:
        open_id = "ou_current"
        user_id = "cli_user_current"
        union_id = "on_current"

    monkeypatch.setattr(
        "feishu_bot_sdk.bitable.BitableService.grant_edit_permission", _fake_grant
    )
    monkeypatch.setattr(
        "feishu_bot_sdk.feishu.FeishuClient.get_user_info",
        lambda _self, user_access_token=None: _FakeUserInfo(),
    )

    code = cli.main(
        [
            "bitable",
            "grant-edit",
            "--app-token",
            "app_1",
            "--member-id",
            "me",
            "--member-id-type",
            "union_id",
            "--auth-mode",
            "user",
        ]
    )
    assert code == 0
    assert called["grant"] == ("app_1", "on_current", "union_id")
    assert "ok" in capsys.readouterr().out


def test_bitable_list_records_all(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    calls: list[dict[str, Any]] = []

    def _fake_list_records(
        _self: BitableService,
        app_token: str,
        table_id: str,
        *,
        page_size: int | None = None,
        page_token: str | None = None,
        view_id: str | None = None,
        user_id_type: str | None = None,
        filter: str | None = None,
        sort: str | None = None,
        field_names: str | None = None,
        text_field_as_array: bool | None = None,
    ) -> dict[str, Any]:
        calls.append(
            {
                "app_token": app_token,
                "table_id": table_id,
                "page_size": page_size,
                "page_token": page_token,
                "view_id": view_id,
                "user_id_type": user_id_type,
                "filter": filter,
                "sort": sort,
                "field_names": field_names,
                "text_field_as_array": text_field_as_array,
            }
        )
        if page_token == "next_1":
            return {"items": [{"record_id": "rec_2"}], "has_more": False}
        return {
            "items": [{"record_id": "rec_1"}],
            "has_more": True,
            "page_token": "next_1",
        }

    monkeypatch.setattr(
        "feishu_bot_sdk.bitable.BitableService.list_records", _fake_list_records
    )

    code = cli.main(
        [
            "bitable",
            "list-records",
            "--app-token",
            "app_1",
            "--table-id",
            "tbl_1",
            "--view-id",
            "vew_1",
            "--user-id-type",
            "open_id",
            "--filter",
            'CurrentValue.[状态]="进行中"',
            "--sort",
            '[{"field_name":"创建时间","desc":true}]',
            "--field-names",
            '["任务名称"]',
            "--text-field-as-array",
            "true",
            "--all",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert len(calls) == 2
    assert calls[0]["app_token"] == "app_1"
    assert calls[0]["table_id"] == "tbl_1"
    assert calls[0]["view_id"] == "vew_1"
    assert calls[0]["user_id_type"] == "open_id"
    assert calls[0]["text_field_as_array"] is True
    assert calls[1]["page_token"] == "next_1"
    payload = json.loads(capsys.readouterr().out)
    assert payload["all"] is True
    assert payload["count"] == 2
    assert [item["record_id"] for item in payload["items"]] == ["rec_1", "rec_2"]
