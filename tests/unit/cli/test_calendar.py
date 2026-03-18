import io
import json
from typing import Any
from feishu_bot_sdk import cli
from feishu_bot_sdk.calendar import CalendarService
from feishu_bot_sdk.drive import DriveFileService


def test_calendar_list_calendars(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    captured: dict[str, Any] = {}

    def _fake_list_calendars(
        _self: CalendarService,
        *,
        page_size: int | None = None,
        page_token: str | None = None,
        sync_token: str | None = None,
    ) -> dict[str, Any]:
        captured["page_size"] = page_size
        captured["page_token"] = page_token
        captured["sync_token"] = sync_token
        return {"items": [{"calendar_id": "cal_1"}], "has_more": False}

    monkeypatch.setattr(
        "feishu_bot_sdk.calendar.CalendarService.list_calendars", _fake_list_calendars
    )

    code = cli.main(
        [
            "calendar",
            "list-calendars",
            "--page-size",
            "10",
            "--sync-token",
            "sync_1",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert captured["page_size"] == 10
    assert captured["sync_token"] == "sync_1"
    payload = json.loads(capsys.readouterr().out)
    assert payload["items"][0]["calendar_id"] == "cal_1"


def test_calendar_list_calendars_all(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    calls: list[str | None] = []

    def _fake_list_calendars(
        _self: CalendarService,
        *,
        page_size: int | None = None,
        page_token: str | None = None,
        sync_token: str | None = None,
    ) -> dict[str, Any]:
        calls.append(page_token)
        if page_token == "next_1":
            return {"items": [{"calendar_id": "cal_2"}], "has_more": False}
        return {"items": [{"calendar_id": "cal_1"}], "has_more": True, "page_token": "next_1"}

    monkeypatch.setattr(
        "feishu_bot_sdk.calendar.CalendarService.list_calendars", _fake_list_calendars
    )

    code = cli.main(["calendar", "list-calendars", "--all", "--format", "json"])
    assert code == 0
    assert calls == [None, "next_1"]
    payload = json.loads(capsys.readouterr().out)
    assert payload["all"] is True
    assert payload["count"] == 2
    assert [item["calendar_id"] for item in payload["items"]] == ["cal_1", "cal_2"]


def test_calendar_create_event_from_stdin(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")
    monkeypatch.setattr("sys.stdin", io.StringIO('{"summary":"Kickoff"}'))

    captured: dict[str, Any] = {}

    def _fake_create_event(
        _self: CalendarService,
        calendar_id: str,
        event: dict[str, Any],
        *,
        user_id_type: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        captured["calendar_id"] = calendar_id
        captured["event"] = event
        captured["user_id_type"] = user_id_type
        captured["idempotency_key"] = idempotency_key
        return {"event_id": "evt_1"}

    monkeypatch.setattr(
        "feishu_bot_sdk.calendar.CalendarService.create_event", _fake_create_event
    )

    code = cli.main(
        [
            "calendar",
            "create-event",
            "--calendar-id",
            "cal_1",
            "--event-stdin",
            "--user-id-type",
            "open_id",
            "--idempotency-key",
            "idem_1",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert captured["calendar_id"] == "cal_1"
    assert captured["event"] == {"summary": "Kickoff"}
    assert captured["user_id_type"] == "open_id"
    assert captured["idempotency_key"] == "idem_1"
    payload = json.loads(capsys.readouterr().out)
    assert payload["event_id"] == "evt_1"


def test_calendar_delete_event_with_need_notification(
    monkeypatch: Any, capsys: Any
) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    captured: dict[str, Any] = {}

    def _fake_delete_event(
        _self: CalendarService,
        calendar_id: str,
        event_id: str,
        *,
        need_notification: bool | None = None,
    ) -> dict[str, Any]:
        captured["calendar_id"] = calendar_id
        captured["event_id"] = event_id
        captured["need_notification"] = need_notification
        return {"ok": True}

    monkeypatch.setattr(
        "feishu_bot_sdk.calendar.CalendarService.delete_event", _fake_delete_event
    )

    code = cli.main(
        [
            "calendar",
            "delete-event",
            "--calendar-id",
            "cal_1",
            "--event-id",
            "evt_1",
            "--need-notification",
            "true",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert captured["calendar_id"] == "cal_1"
    assert captured["event_id"] == "evt_1"
    assert captured["need_notification"] is True
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True


def test_calendar_attach_material_append(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    captured: dict[str, Any] = {}

    def _fake_upload_media(
        _self: DriveFileService,
        path: str,
        *,
        parent_type: str,
        parent_node: str,
        file_name: str | None = None,
        extra: str | None = None,
        checksum: str | None = None,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        captured["upload"] = {
            "path": path,
            "parent_type": parent_type,
            "parent_node": parent_node,
            "file_name": file_name,
            "content_type": content_type,
        }
        return {"file_token": "file_new_1", "name": "brief.md"}

    def _fake_get_event(
        _self: CalendarService,
        calendar_id: str,
        event_id: str,
        *,
        need_meeting_settings: bool | None = None,
        need_attendee: bool | None = None,
        max_attendee_num: int | None = None,
        user_id_type: str | None = None,
    ) -> dict[str, Any]:
        captured["get"] = {
            "calendar_id": calendar_id,
            "event_id": event_id,
            "user_id_type": user_id_type,
        }
        return {
            "event": {"attachments": [{"file_token": "file_old_1", "name": "old.txt"}]}
        }

    def _fake_update_event(
        _self: CalendarService,
        calendar_id: str,
        event_id: str,
        event: dict[str, Any],
        *,
        user_id_type: str | None = None,
    ) -> dict[str, Any]:
        captured["update"] = {
            "calendar_id": calendar_id,
            "event_id": event_id,
            "event": event,
            "user_id_type": user_id_type,
        }
        return {
            "event": {"event_id": event_id, "attachments": event.get("attachments", [])}
        }

    monkeypatch.setattr(
        "feishu_bot_sdk.drive.DriveFileService.upload_media", _fake_upload_media
    )
    monkeypatch.setattr(
        "feishu_bot_sdk.calendar.CalendarService.get_event", _fake_get_event
    )
    monkeypatch.setattr(
        "feishu_bot_sdk.calendar.CalendarService.update_event", _fake_update_event
    )

    code = cli.main(
        [
            "calendar",
            "attach-material",
            "--calendar-id",
            "cal_1",
            "--event-id",
            "evt_1",
            "--path",
            "./brief.md",
            "--mode",
            "append",
            "--need-notification",
            "false",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert captured["upload"]["parent_type"] == "calendar"
    assert captured["upload"]["parent_node"] == "cal_1"
    assert captured["update"]["event"]["need_notification"] is False
    assert captured["update"]["event"]["attachments"] == [
        {"file_token": "file_old_1", "name": "old.txt"},
        {"file_token": "file_new_1", "name": "brief.md"},
    ]
    payload = json.loads(capsys.readouterr().out)
    assert payload["file_token"] == "file_new_1"
    assert payload["attachments_count"] == 2
