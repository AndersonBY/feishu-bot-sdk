import json
from typing import Any
from feishu_bot_sdk import cli
from feishu_bot_sdk.calendar import CalendarService
from feishu_bot_sdk.drive import DriveFileService


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
            "+attach-material",
            "./brief.md",
            "--calendar-id",
            "cal_1",
            "--event-id",
            "evt_1",
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
