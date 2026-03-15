import json
from typing import Any
from feishu_bot_sdk import cli
from feishu_bot_sdk.bot import BotService


def test_bot_info_json_output(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    def _fake_get_info(_self: BotService) -> dict[str, Any]:
        return {
            "app_name": "CLI Bot",
            "open_id": "ou_cli_bot_1",
        }

    monkeypatch.setattr("feishu_bot_sdk.bot.BotService.get_info", _fake_get_info)

    code = cli.main(["bot", "info", "--format", "json"])
    assert code == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["app_name"] == "CLI Bot"
    assert payload["open_id"] == "ou_cli_bot_1"
