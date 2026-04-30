from __future__ import annotations

import json
from typing import Any

import feishu_bot_sdk.cli as cli
from feishu_bot_sdk.feishu import FeishuClient


def test_calendar_help_lists_lark_shortcuts(capsys: Any) -> None:
    code = cli.main(["calendar", "--help"])

    assert code == 0
    output = capsys.readouterr().out
    for command in ("+agenda", "+create", "+freebusy", "+room-find", "+suggestion", "+update"):
        assert command in output


def test_calendar_create_adds_event_and_attendees(monkeypatch: Any, capsys: Any) -> None:
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
        if path == "/calendar/v4/calendars/primary/events":
            assert payload is not None
            return {"code": 0, "data": {"event": {"event_id": "evt_1", "summary": payload["summary"]}}}
        return {"code": 0, "data": {}}

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)

    code = cli.main(
        [
            "calendar",
            "+create",
            "--as",
            "bot",
            "--app-id",
            "cli_app",
            "--app-secret",
            "cli_secret",
            "--summary",
            "Planning",
            "--start",
            "2026-04-29T10:00:00+08:00",
            "--end",
            "2026-04-29T11:00:00+08:00",
            "--attendee-ids",
            "ou_1,oc_1,omm_1",
            "--format",
            "json",
        ]
    )

    assert code == 0
    assert calls[0]["method"] == "POST"
    assert calls[0]["path"] == "/calendar/v4/calendars/primary/events"
    assert calls[0]["payload"]["summary"] == "Planning"
    assert calls[0]["payload"]["vchat"] == {"vc_type": "vc"}
    assert calls[1] == {
        "method": "POST",
        "path": "/calendar/v4/calendars/primary/events/evt_1/attendees",
        "payload": {
            "attendees": [
                {"type": "user", "user_id": "ou_1"},
                {"type": "chat", "chat_id": "oc_1"},
                {"type": "resource", "room_id": "omm_1"},
            ],
            "need_notification": True,
        },
        "params": {"user_id_type": "open_id"},
    }
    payload = json.loads(capsys.readouterr().out)
    assert payload["event_id"] == "evt_1"


def test_calendar_update_runs_patch_remove_add(monkeypatch: Any, capsys: Any) -> None:
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
        return {"code": 0, "data": {"event": {"event_id": "evt_1", "summary": "Updated"}}}

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)

    code = cli.main(
        [
            "calendar",
            "+update",
            "--as",
            "bot",
            "--app-id",
            "cli_app",
            "--app-secret",
            "cli_secret",
            "--calendar-id",
            "cal_1",
            "--event-id",
            "evt_1",
            "--summary",
            "Updated",
            "--add-attendee-ids",
            "ou_add",
            "--remove-attendee-ids",
            "ou_remove",
            "--format",
            "json",
        ]
    )

    assert code == 0
    assert calls[0]["method"] == "PATCH"
    assert calls[0]["path"] == "/calendar/v4/calendars/cal_1/events/evt_1"
    assert calls[0]["payload"] == {"summary": "Updated", "need_notification": True}
    assert calls[1]["path"] == "/calendar/v4/calendars/cal_1/events/evt_1/attendees/batch_delete"
    assert calls[1]["payload"]["delete_ids"] == [{"type": "user", "user_id": "ou_remove"}]
    assert calls[2]["path"] == "/calendar/v4/calendars/cal_1/events/evt_1/attendees"
    assert calls[2]["payload"]["attendees"] == [{"type": "user", "user_id": "ou_add"}]


def test_calendar_read_shortcuts_build_requests(monkeypatch: Any, capsys: Any) -> None:
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
        if path.endswith("/events/instance_view"):
            return {"code": 0, "data": {"items": [{"event_id": "evt_1", "summary": "Planning"}]}}
        if path == "/calendar/v4/freebusy/list":
            return {"code": 0, "data": {"freebusy_list": [{"start_time": "a", "end_time": "b"}]}}
        if path == "/calendar/v4/freebusy/suggestion":
            return {"code": 0, "data": {"suggestions": [{"event_start_time": "a", "event_end_time": "b"}]}}
        if path == "/calendar/v4/freebusy/meeting_room/search":
            return {"code": 0, "data": {"available_rooms": [{"room_id": "omm_1", "room_name": "R1"}]}}
        raise AssertionError(f"unexpected path: {path}")

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)

    base = ["--as", "bot", "--app-id", "cli_app", "--app-secret", "cli_secret", "--format", "json"]
    assert (
        cli.main(
            [
                "calendar",
                "+agenda",
                *base,
                "--calendar-id",
                "cal_1",
                "--start",
                "2026-04-29T00:00:00+08:00",
                "--end",
                "2026-04-29T01:00:00+08:00",
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert cli.main(["calendar", "+freebusy", *base, "--user-id", "ou_1", "--start", "2026-04-29", "--end", "2026-04-29"]) == 0
    capsys.readouterr()
    assert cli.main(["calendar", "+suggestion", *base, "--attendee-ids", "ou_1,oc_1", "--duration-minutes", "30"]) == 0
    capsys.readouterr()
    assert cli.main(["calendar", "+room-find", *base, "--slot", "2026-04-29T10:00:00+08:00~2026-04-29T11:00:00+08:00", "--min-capacity", "4"]) == 0

    assert calls[0]["method"] == "GET"
    assert calls[0]["path"] == "/calendar/v4/calendars/cal_1/events/instance_view"
    assert calls[0]["params"]["start_time"] == "1777392000"
    assert calls[0]["params"]["end_time"] == "1777395600"
    assert calls[1]["method"] == "POST"
    assert calls[1]["path"] == "/calendar/v4/freebusy/list"
    assert calls[1]["payload"]["user_id"] == "ou_1"
    assert calls[2]["method"] == "POST"
    assert calls[2]["path"] == "/calendar/v4/freebusy/suggestion"
    assert calls[2]["payload"]["duration_minutes"] == 30
    assert calls[2]["payload"]["attendee_user_ids"] == ["ou_1"]
    assert calls[2]["payload"]["attendee_chat_ids"] == ["oc_1"]
    assert calls[3]["method"] == "POST"
    assert calls[3]["path"] == "/calendar/v4/freebusy/meeting_room/search"
    assert calls[3]["payload"]["min_capacity"] == 4
