from __future__ import annotations

import json
from typing import Any

import feishu_bot_sdk.cli as cli
from feishu_bot_sdk.feishu import FeishuClient


def test_whiteboard_help_lists_lark_shortcuts(capsys: Any) -> None:
    code = cli.main(["whiteboard", "--help"])

    assert code == 0
    output = capsys.readouterr().out
    assert "+query" in output
    assert "+update" in output


def test_whiteboard_query_raw_and_update_mermaid(monkeypatch: Any, tmp_path: Any, capsys: Any) -> None:
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
        if path == "/board/v1/whiteboards/wb_1/nodes" and method == "GET":
            return {"code": 0, "data": {"nodes": [{"id": "node_1", "type": "shape"}]}}
        if path == "/board/v1/whiteboards/wb_1/nodes/plantuml":
            return {"code": 0, "data": {"node_id": "node_new"}}
        raise AssertionError(f"unexpected path: {path}")

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)
    source = tmp_path / "diagram.mmd"
    source.write_text("graph TD\nA-->B\n", encoding="utf-8")
    base = ["--as", "bot", "--app-id", "cli_app", "--app-secret", "cli_secret", "--format", "json"]

    assert cli.main(["whiteboard", "+query", *base, "--whiteboard-token", "wb_1", "--output-as", "raw"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["nodes"] == [{"id": "node_1", "type": "shape"}]

    assert (
        cli.main(
            [
                "whiteboard",
                "+update",
                *base,
                "--whiteboard-token",
                "wb_1",
                "--source",
                f"@{source}",
                "--input-format",
                "mermaid",
                "--overwrite",
                "--idempotent-token",
                "idempotent1",
            ]
        )
        == 0
    )

    assert calls[0] == {
        "method": "GET",
        "path": "/board/v1/whiteboards/wb_1/nodes",
        "payload": None,
        "params": None,
    }
    assert calls[1] == {
        "method": "POST",
        "path": "/board/v1/whiteboards/wb_1/nodes/plantuml",
        "payload": {
            "plant_uml_code": "graph TD\nA-->B\n",
            "syntax_type": 2,
            "parse_mode": 1,
            "diagram_type": 0,
            "overwrite": True,
        },
        "params": {"client_token": "idempotent1"},
    }


def test_docs_whiteboard_update_alias(monkeypatch: Any, tmp_path: Any, capsys: Any) -> None:
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
        return {"code": 0, "data": {"node_id": "node_new"}}

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)
    source = tmp_path / "diagram.puml"
    source.write_text("@startuml\nA -> B\n@enduml\n", encoding="utf-8")

    code = cli.main(
        [
            "docs",
            "+whiteboard-update",
            "--as",
            "bot",
            "--app-id",
            "cli_app",
            "--app-secret",
            "cli_secret",
            "--whiteboard-token",
            "wb_1",
            "--source",
            f"@{source}",
            "--input-format",
            "plantuml",
            "--format",
            "json",
        ]
    )

    assert code == 0
    capsys.readouterr()
    assert calls[0]["path"] == "/board/v1/whiteboards/wb_1/nodes/plantuml"
    assert calls[0]["payload"]["syntax_type"] == 1
