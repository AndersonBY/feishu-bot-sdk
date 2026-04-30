from __future__ import annotations

import json
from typing import Any

import feishu_bot_sdk.cli as cli


def test_update_check_reports_python_distribution_policy(capsys: Any) -> None:
    code = cli.main(["update", "--check", "--format", "json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["action"] in {"already_up_to_date", "manual_required", "update_available"}
    assert payload["package"] == "feishu-bot-sdk"
    assert payload["auto_update"] is False
    assert payload["current_version"]
    assert payload["latest_version"]
    assert "pip install" in payload["hint"]


def test_update_force_is_manual_for_python_package(capsys: Any) -> None:
    code = cli.main(["update", "--force", "--format", "json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["action"] == "manual_required"
    assert payload["auto_update"] is False
