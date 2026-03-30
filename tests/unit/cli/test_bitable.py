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
            "+create-from-csv",
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
            "+create-from-csv",
            "final.csv",
            "--app-name",
            "A",
            "--table-name",
            "T",
            "--grant-member-id",
            "me",
            "--member-id-type",
            "user_id",
            "--as",
            "user",
        ]
    )
    assert code == 0
    assert called["csv_path"] == "final.csv"
    assert called["grant"] == ("app_token_2", "cli_user_current", "user_id")
    assert "app_token" in capsys.readouterr().out
