import json
from pathlib import Path
from typing import Any

from feishu_bot_sdk import cli


def _large_payload() -> dict[str, Any]:
    return {
        "items": [
            {
                "app_id": f"cli_{index}",
                "name": f"app-{index}-" + ("x" * 2500),
                "description": "y" * 2500,
            }
            for index in range(30)
        ],
        "has_more": True,
        "page_token": "next_1",
    }


def test_large_output_is_truncated_with_paging_hints(
    monkeypatch: Any, capsys: Any
) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    monkeypatch.setattr(
        "feishu_bot_sdk.feishu.FeishuClient.request_json",
        lambda _self, method, path, params=None, payload=None: _large_payload(),
    )

    code = cli.main(
        [
            "api",
            "GET",
            "/test/large",
            "--max-output-chars",
            "4000",
            "--format",
            "json",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert len(out) <= 4000
    payload = json.loads(out)
    assert payload["_cli_output"]["truncated"] is True
    assert payload["_cli_output"]["mode"] == "preview"
    assert any("output-offset" in hint for hint in payload["_cli_output"]["hints"])
    assert len(payload["items"]) < 30


def test_output_offset_returns_json_slice(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    monkeypatch.setattr(
        "feishu_bot_sdk.feishu.FeishuClient.request_json",
        lambda _self, method, path, params=None, payload=None: _large_payload(),
    )

    code = cli.main(
        [
            "api",
            "GET",
            "/test/large",
            "--output-offset",
            "1200",
            "--max-output-chars",
            "2500",
            "--format",
            "json",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert len(out) <= 2500
    payload = json.loads(out)
    assert payload["_cli_output"]["mode"] == "json_slice"
    assert payload["_cli_output"]["output_offset"] == 1200
    assert isinstance(payload["json_slice"], str)
    assert payload["json_slice"]


def test_save_output_writes_full_json_before_truncation(
    monkeypatch: Any, tmp_path: Path, capsys: Any
) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    monkeypatch.setattr(
        "feishu_bot_sdk.feishu.FeishuClient.request_json",
        lambda _self, method, path, params=None, payload=None: _large_payload(),
    )

    output_path = tmp_path / "full.json"
    code = cli.main(
        [
            "api",
            "GET",
            "/test/large",
            "--save-output",
            str(output_path),
            "--max-output-chars",
            "3000",
            "--format",
            "json",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert len(out) <= 3000
    payload = json.loads(out)
    assert payload["_cli_output"]["save_output"] == str(output_path)
    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert len(saved["items"]) == 30
    assert saved["page_token"] == "next_1"


def test_full_output_disables_truncation(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    monkeypatch.setattr(
        "feishu_bot_sdk.feishu.FeishuClient.request_json",
        lambda _self, method, path, params=None, payload=None: _large_payload(),
    )

    code = cli.main(
        [
            "api",
            "GET",
            "/test/large",
            "--full-output",
            "--max-output-chars",
            "3000",
            "--format",
            "json",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert len(out) > 3000
    payload = json.loads(out)
    assert "_cli_output" not in payload
    assert len(payload["items"]) == 30
