import json
from pathlib import Path
from typing import Any

from feishu_bot_sdk import cli
from feishu_bot_sdk.search import SearchService


def _large_search_payload() -> dict[str, Any]:
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


def test_large_search_output_is_truncated_with_paging_hints(
    monkeypatch: Any, capsys: Any
) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")
    monkeypatch.setenv("FEISHU_USER_ACCESS_TOKEN", "u_cli_dummy")

    monkeypatch.setattr(
        "feishu_bot_sdk.search.SearchService.search_apps",
        lambda _self, query, user_id_type=None, page_size=None, page_token=None: _large_search_payload(),
    )

    code = cli.main(
        [
            "search",
            "app",
            "--query",
            "calendar",
            "--page-size",
            "30",
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
    assert payload["_cli_output"]["paging"]["next_page_token"] == "next_1"
    assert any("page-token next_1" in hint for hint in payload["_cli_output"]["hints"])
    assert any("output-offset" in hint for hint in payload["_cli_output"]["hints"])
    assert len(payload["items"]) < 30


def test_output_offset_returns_json_slice(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")
    monkeypatch.setenv("FEISHU_USER_ACCESS_TOKEN", "u_cli_dummy")

    monkeypatch.setattr(
        "feishu_bot_sdk.search.SearchService.search_apps",
        lambda _self, query, user_id_type=None, page_size=None, page_token=None: _large_search_payload(),
    )

    code = cli.main(
        [
            "search",
            "app",
            "--query",
            "calendar",
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
    monkeypatch.setenv("FEISHU_USER_ACCESS_TOKEN", "u_cli_dummy")

    monkeypatch.setattr(
        "feishu_bot_sdk.search.SearchService.search_apps",
        lambda _self, query, user_id_type=None, page_size=None, page_token=None: _large_search_payload(),
    )

    output_path = tmp_path / "search-full.json"
    code = cli.main(
        [
            "search",
            "app",
            "--query",
            "calendar",
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
    monkeypatch.setenv("FEISHU_USER_ACCESS_TOKEN", "u_cli_dummy")

    monkeypatch.setattr(
        "feishu_bot_sdk.search.SearchService.search_apps",
        lambda _self, query, user_id_type=None, page_size=None, page_token=None: _large_search_payload(),
    )

    code = cli.main(
        [
            "search",
            "app",
            "--query",
            "calendar",
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
