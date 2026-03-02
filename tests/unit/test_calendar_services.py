import asyncio
from typing import Any, Mapping, Optional, cast

from feishu_bot_sdk.calendar import AsyncCalendarService, CalendarService
from feishu_bot_sdk.feishu import AsyncFeishuClient, FeishuClient


class _SyncClientStub:
    def __init__(self, resolver: Any) -> None:
        self._resolver = resolver
        self.calls: list[dict[str, Any]] = []

    def request_json(
        self,
        method: str,
        path: str,
        *,
        payload: Optional[Mapping[str, object]] = None,
        params: Optional[Mapping[str, object]] = None,
    ) -> Mapping[str, Any]:
        call = {
            "method": method,
            "path": path,
            "payload": dict(payload or {}),
            "params": dict(params or {}),
        }
        self.calls.append(call)
        return self._resolver(call)


class _AsyncClientStub:
    def __init__(self, resolver: Any) -> None:
        self._resolver = resolver
        self.calls: list[dict[str, Any]] = []

    async def request_json(
        self,
        method: str,
        path: str,
        *,
        payload: Optional[Mapping[str, object]] = None,
        params: Optional[Mapping[str, object]] = None,
    ) -> Mapping[str, Any]:
        call = {
            "method": method,
            "path": path,
            "payload": dict(payload or {}),
            "params": dict(params or {}),
        }
        self.calls.append(call)
        return self._resolver(call)


def test_calendar_core_requests() -> None:
    def resolver(_call: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"code": 0, "data": {"ok": True}}

    stub = _SyncClientStub(resolver)
    service = CalendarService(cast(FeishuClient, stub))

    service.primary_calendar(user_id_type="user_id")
    service.list_calendars(page_size=20, page_token="p1", sync_token="s1")
    service.create_calendar({"summary": "Team Calendar"})
    service.get_calendar("cal_1")
    service.update_calendar("cal_1", {"summary": "New Summary"})
    service.delete_calendar("cal_1")
    service.search_calendars("team", page_size=10, page_token="p2")

    assert len(stub.calls) == 7
    assert stub.calls[0]["path"] == "/calendar/v4/calendars/primary"
    assert stub.calls[0]["params"] == {"user_id_type": "user_id"}
    assert stub.calls[1]["path"] == "/calendar/v4/calendars"
    assert stub.calls[1]["params"] == {"page_size": 20, "page_token": "p1", "sync_token": "s1"}
    assert stub.calls[2]["method"] == "POST"
    assert stub.calls[2]["payload"] == {"summary": "Team Calendar"}
    assert stub.calls[3]["path"] == "/calendar/v4/calendars/cal_1"
    assert stub.calls[4]["method"] == "PATCH"
    assert stub.calls[5]["method"] == "DELETE"
    assert stub.calls[6]["path"] == "/calendar/v4/calendars/search"
    assert stub.calls[6]["payload"] == {"query": "team"}


def test_calendar_event_and_freebusy_requests() -> None:
    def resolver(_call: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"code": 0, "data": {"ok": True}}

    stub = _SyncClientStub(resolver)
    service = CalendarService(cast(FeishuClient, stub))

    service.create_event(
        "cal_1",
        {"summary": "Kickoff"},
        user_id_type="open_id",
        idempotency_key="idem_1",
    )
    service.get_event(
        "cal_1",
        "evt_1",
        need_attendee=True,
        need_meeting_settings=True,
        max_attendee_num=50,
        user_id_type="open_id",
    )
    service.list_events(
        "cal_1",
        page_size=20,
        page_token="p1",
        sync_token="s1",
        start_time="1700000000",
        end_time="1700003600",
        anchor_time="1700000000",
        user_id_type="open_id",
    )
    service.update_event("cal_1", "evt_1", {"summary": "Updated"}, user_id_type="open_id")
    service.delete_event("cal_1", "evt_1", need_notification=True)
    service.search_events(
        "cal_1",
        "kickoff",
        page_size=10,
        page_token="p2",
        user_id_type="open_id",
        search_filter={"field_filters": []},
    )
    service.reply_event("cal_1", "evt_1", {"rsvp_status": "accept"})
    service.list_freebusy(
        {"time_min": "2020-10-28T12:00:00+08:00", "time_max": "2020-12-28T12:00:00+08:00"},
        user_id_type="open_id",
    )
    service.batch_freebusy({"time_min": "a", "time_max": "b"}, user_id_type="open_id")
    service.generate_caldav_conf({"device_name": "iPhone"})

    assert len(stub.calls) == 10
    assert stub.calls[0]["path"] == "/calendar/v4/calendars/cal_1/events"
    assert stub.calls[0]["params"] == {"user_id_type": "open_id", "idempotency_key": "idem_1"}
    assert stub.calls[1]["path"] == "/calendar/v4/calendars/cal_1/events/evt_1"
    assert stub.calls[1]["params"]["need_attendee"] is True
    assert stub.calls[2]["path"] == "/calendar/v4/calendars/cal_1/events"
    assert stub.calls[4]["method"] == "DELETE"
    assert stub.calls[4]["params"] == {"need_notification": True}
    assert stub.calls[5]["path"] == "/calendar/v4/calendars/cal_1/events/search"
    assert stub.calls[5]["payload"] == {"query": "kickoff", "filter": {"field_filters": []}}
    assert stub.calls[6]["path"] == "/calendar/v4/calendars/cal_1/events/evt_1/reply"
    assert stub.calls[7]["path"] == "/calendar/v4/freebusy/list"
    assert stub.calls[8]["path"] == "/calendar/v4/freebusy/batch"
    assert stub.calls[9]["path"] == "/calendar/v4/settings/generate_caldav_conf"


def test_async_calendar_iteration() -> None:
    def resolver(call: Mapping[str, Any]) -> Mapping[str, Any]:
        if call["path"] == "/calendar/v4/calendars":
            page_token = call["params"].get("page_token")
            if page_token == "next":
                return {"code": 0, "data": {"items": [{"calendar_id": "cal_2"}], "has_more": False}}
            return {
                "code": 0,
                "data": {"items": [{"calendar_id": "cal_1"}], "has_more": True, "page_token": "next"},
            }
        if call["path"] == "/calendar/v4/calendars/cal_1/events":
            page_token = call["params"].get("page_token")
            if page_token == "evt_next":
                return {"code": 0, "data": {"items": [{"event_id": "evt_2"}], "has_more": False}}
            return {
                "code": 0,
                "data": {"items": [{"event_id": "evt_1"}], "has_more": True, "page_token": "evt_next"},
            }
        return {"code": 0, "data": {"ok": True}}

    stub = _AsyncClientStub(resolver)
    service = AsyncCalendarService(cast(AsyncFeishuClient, stub))

    async def run() -> None:
        calendars: list[Mapping[str, Any]] = []
        events: list[Mapping[str, Any]] = []
        async for item in service.iter_calendars(page_size=1):
            calendars.append(item)
        async for item in service.iter_events("cal_1", page_size=1):
            events.append(item)
        assert calendars == [{"calendar_id": "cal_1"}, {"calendar_id": "cal_2"}]
        assert events == [{"event_id": "evt_1"}, {"event_id": "evt_2"}]

    asyncio.run(run())
    assert stub.calls[0]["path"] == "/calendar/v4/calendars"
    assert stub.calls[1]["params"] == {"page_size": 1, "page_token": "next"}
    assert stub.calls[2]["path"] == "/calendar/v4/calendars/cal_1/events"
    assert stub.calls[3]["params"] == {"page_size": 1, "page_token": "evt_next"}
