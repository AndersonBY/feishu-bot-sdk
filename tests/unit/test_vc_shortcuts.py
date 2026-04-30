from __future__ import annotations

import json
from typing import Any

import feishu_bot_sdk.cli as cli
from feishu_bot_sdk.feishu import FeishuClient


def test_vc_help_lists_lark_shortcuts(capsys: Any) -> None:
    code = cli.main(["vc", "--help"])

    assert code == 0
    output = capsys.readouterr().out
    assert "+search" in output
    assert "+notes" in output
    assert "+recording" in output


def test_vc_search_builds_meeting_filter_payload(monkeypatch: Any, capsys: Any) -> None:
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
                "items": [{"id": "m_1", "display_info": "Weekly meeting"}],
                "has_more": False,
                "total": 1,
            },
        }

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)

    code = cli.main(
        [
            "vc",
            "+search",
            "--as",
            "user",
            "--user-access-token",
            "user_token",
            "--query",
            "Weekly",
            "--organizer-ids",
            "ou_owner",
            "--participant-ids",
            "ou_a,ou_a,ou_b",
            "--room-ids",
            "omm_1",
            "--page-size",
            "8",
            "--format",
            "json",
        ]
    )

    assert code == 0
    assert captured == {
        "method": "POST",
        "path": "/vc/v1/meetings/search",
        "payload": {
            "query": "Weekly",
            "meeting_filter": {
                "participant_ids": ["ou_a", "ou_b"],
                "organizer_ids": ["ou_owner"],
                "open_room_ids": ["omm_1"],
            },
        },
        "params": {"page_size": 8},
    }
    payload = json.loads(capsys.readouterr().out)
    assert payload["items"][0]["id"] == "m_1"


def test_vc_notes_resolves_meeting_note_detail(monkeypatch: Any, capsys: Any) -> None:
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
        if path == "/vc/v1/meetings/m_1":
            return {"code": 0, "data": {"meeting": {"id": "m_1", "note_id": "note_1"}}}
        if path == "/vc/v1/notes/note_1":
            return {
                "code": 0,
                "data": {
                    "note": {
                        "creator_id": "ou_creator",
                        "create_time": "1710000000",
                        "artifacts": [
                            {"artifact_type": 1, "doc_token": "doc_note"},
                            {"artifact_type": 2, "doc_token": "doc_verbatim"},
                        ],
                        "references": [{"doc_token": "doc_shared"}],
                    }
                },
            }
        raise AssertionError(f"unexpected path: {path}")

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)

    code = cli.main(
        [
            "vc",
            "+notes",
            "--as",
            "user",
            "--user-access-token",
            "user_token",
            "--meeting-ids",
            "m_1",
            "--format",
            "json",
        ]
    )

    assert code == 0
    assert calls == [
        {
            "method": "GET",
            "path": "/vc/v1/meetings/m_1",
            "payload": None,
            "params": {"with_participants": "false", "query_mode": "0"},
        },
        {"method": "GET", "path": "/vc/v1/notes/note_1", "payload": None, "params": None},
    ]
    payload = json.loads(capsys.readouterr().out)
    assert payload["notes"][0]["meeting_id"] == "m_1"
    assert payload["notes"][0]["note_doc_token"] == "doc_note"
    assert payload["notes"][0]["verbatim_doc_token"] == "doc_verbatim"
    assert payload["notes"][0]["shared_doc_tokens"] == ["doc_shared"]


def test_vc_recording_extracts_minute_token(monkeypatch: Any, capsys: Any) -> None:
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
                "recording": {
                    "url": "https://meetings.feishu.cn/minutes/min_token_1",
                    "duration": "600",
                }
            },
        }

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)

    code = cli.main(
        [
            "vc",
            "+recording",
            "--as",
            "user",
            "--user-access-token",
            "user_token",
            "--meeting-ids",
            "m_1",
            "--format",
            "json",
        ]
    )

    assert code == 0
    assert captured == {
        "method": "GET",
        "path": "/vc/v1/meetings/m_1/recording",
        "payload": None,
        "params": None,
    }
    payload = json.loads(capsys.readouterr().out)
    assert payload["recordings"][0]["meeting_id"] == "m_1"
    assert payload["recordings"][0]["minute_token"] == "min_token_1"
