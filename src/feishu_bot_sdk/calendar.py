from typing import Any, AsyncIterator, Iterator, Mapping, Optional

from .feishu import AsyncFeishuClient, FeishuClient
from .response import DataResponse


def _drop_none(params: Mapping[str, object]) -> dict[str, object]:
    return {key: value for key, value in params.items() if value is not None}


def _unwrap_data(response: Mapping[str, Any]) -> DataResponse:
    return DataResponse.from_raw(response)


def _iter_page_items(data: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
    items = data.get("items")
    if not isinstance(items, list):
        return
    for item in items:
        if isinstance(item, Mapping):
            yield item


def _next_page_token(data: Mapping[str, Any]) -> Optional[str]:
    token = data.get("page_token")
    if isinstance(token, str) and token:
        return token
    return None


def _has_more(data: Mapping[str, Any]) -> bool:
    return bool(data.get("has_more"))


class CalendarService:
    def __init__(self, feishu_client: FeishuClient) -> None:
        self._client = feishu_client

    def primary_calendar(self, *, user_id_type: Optional[str] = None) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        response = self._client.request_json(
            "POST",
            "/calendar/v4/calendars/primary",
            params=params,
        )
        return _unwrap_data(response)

    def list_calendars(
        self,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        sync_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "page_size": page_size,
                "page_token": page_token,
                "sync_token": sync_token,
            }
        )
        response = self._client.request_json("GET", "/calendar/v4/calendars", params=params)
        return _unwrap_data(response)

    def iter_calendars(self, *, page_size: int = 50) -> Iterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = self.list_calendars(page_size=page_size, page_token=page_token)
            yield from _iter_page_items(data)
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    def create_calendar(self, calendar: Mapping[str, object]) -> Mapping[str, Any]:
        response = self._client.request_json("POST", "/calendar/v4/calendars", payload=dict(calendar))
        return _unwrap_data(response)

    def get_calendar(self, calendar_id: str) -> Mapping[str, Any]:
        response = self._client.request_json("GET", f"/calendar/v4/calendars/{calendar_id}")
        return _unwrap_data(response)

    def update_calendar(self, calendar_id: str, calendar: Mapping[str, object]) -> Mapping[str, Any]:
        response = self._client.request_json(
            "PATCH",
            f"/calendar/v4/calendars/{calendar_id}",
            payload=dict(calendar),
        )
        return _unwrap_data(response)

    def delete_calendar(self, calendar_id: str) -> Mapping[str, Any]:
        response = self._client.request_json("DELETE", f"/calendar/v4/calendars/{calendar_id}")
        return _unwrap_data(response)

    def search_calendars(
        self,
        query: str,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"page_size": page_size, "page_token": page_token})
        response = self._client.request_json(
            "POST",
            "/calendar/v4/calendars/search",
            params=params,
            payload={"query": query},
        )
        return _unwrap_data(response)

    def create_event(
        self,
        calendar_id: str,
        event: Mapping[str, object],
        *,
        user_id_type: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type, "idempotency_key": idempotency_key})
        response = self._client.request_json(
            "POST",
            f"/calendar/v4/calendars/{calendar_id}/events",
            params=params,
            payload=dict(event),
        )
        return _unwrap_data(response)

    def get_event(
        self,
        calendar_id: str,
        event_id: str,
        *,
        need_meeting_settings: Optional[bool] = None,
        need_attendee: Optional[bool] = None,
        max_attendee_num: Optional[int] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "need_meeting_settings": need_meeting_settings,
                "need_attendee": need_attendee,
                "max_attendee_num": max_attendee_num,
                "user_id_type": user_id_type,
            }
        )
        response = self._client.request_json(
            "GET",
            f"/calendar/v4/calendars/{calendar_id}/events/{event_id}",
            params=params,
        )
        return _unwrap_data(response)

    def list_events(
        self,
        calendar_id: str,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        sync_token: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        anchor_time: Optional[str] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "page_size": page_size,
                "page_token": page_token,
                "sync_token": sync_token,
                "start_time": start_time,
                "end_time": end_time,
                "anchor_time": anchor_time,
                "user_id_type": user_id_type,
            }
        )
        response = self._client.request_json(
            "GET",
            f"/calendar/v4/calendars/{calendar_id}/events",
            params=params,
        )
        return _unwrap_data(response)

    def iter_events(
        self,
        calendar_id: str,
        *,
        page_size: int = 100,
        sync_token: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        anchor_time: Optional[str] = None,
        user_id_type: Optional[str] = None,
    ) -> Iterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = self.list_events(
                calendar_id,
                page_size=page_size,
                page_token=page_token,
                sync_token=sync_token,
                start_time=start_time,
                end_time=end_time,
                anchor_time=anchor_time,
                user_id_type=user_id_type,
            )
            yield from _iter_page_items(data)
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    def update_event(
        self,
        calendar_id: str,
        event_id: str,
        event: Mapping[str, object],
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        response = self._client.request_json(
            "PATCH",
            f"/calendar/v4/calendars/{calendar_id}/events/{event_id}",
            params=params,
            payload=dict(event),
        )
        return _unwrap_data(response)

    def delete_event(
        self,
        calendar_id: str,
        event_id: str,
        *,
        need_notification: Optional[object] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"need_notification": need_notification})
        response = self._client.request_json(
            "DELETE",
            f"/calendar/v4/calendars/{calendar_id}/events/{event_id}",
            params=params,
        )
        return _unwrap_data(response)

    def search_events(
        self,
        calendar_id: str,
        query: str,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        user_id_type: Optional[str] = None,
        search_filter: Optional[Mapping[str, object]] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "page_size": page_size,
                "page_token": page_token,
                "user_id_type": user_id_type,
            }
        )
        payload: dict[str, object] = {"query": query}
        if search_filter is not None:
            payload["filter"] = dict(search_filter)
        response = self._client.request_json(
            "POST",
            f"/calendar/v4/calendars/{calendar_id}/events/search",
            params=params,
            payload=payload,
        )
        return _unwrap_data(response)

    def reply_event(
        self,
        calendar_id: str,
        event_id: str,
        reply: Mapping[str, object],
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            f"/calendar/v4/calendars/{calendar_id}/events/{event_id}/reply",
            payload=dict(reply),
        )
        return _unwrap_data(response)

    def list_freebusy(
        self,
        request: Mapping[str, object],
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        response = self._client.request_json(
            "POST",
            "/calendar/v4/freebusy/list",
            params=params,
            payload=dict(request),
        )
        return _unwrap_data(response)

    def batch_freebusy(
        self,
        request: Mapping[str, object],
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        response = self._client.request_json(
            "POST",
            "/calendar/v4/freebusy/batch",
            params=params,
            payload=dict(request),
        )
        return _unwrap_data(response)

    def generate_caldav_conf(self, request: Mapping[str, object]) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            "/calendar/v4/settings/generate_caldav_conf",
            payload=dict(request),
        )
        return _unwrap_data(response)


class AsyncCalendarService:
    def __init__(self, feishu_client: AsyncFeishuClient) -> None:
        self._client = feishu_client

    async def primary_calendar(self, *, user_id_type: Optional[str] = None) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        response = await self._client.request_json(
            "POST",
            "/calendar/v4/calendars/primary",
            params=params,
        )
        return _unwrap_data(response)

    async def list_calendars(
        self,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        sync_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "page_size": page_size,
                "page_token": page_token,
                "sync_token": sync_token,
            }
        )
        response = await self._client.request_json("GET", "/calendar/v4/calendars", params=params)
        return _unwrap_data(response)

    async def iter_calendars(self, *, page_size: int = 50) -> AsyncIterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = await self.list_calendars(page_size=page_size, page_token=page_token)
            for item in _iter_page_items(data):
                yield item
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    async def create_calendar(self, calendar: Mapping[str, object]) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            "/calendar/v4/calendars",
            payload=dict(calendar),
        )
        return _unwrap_data(response)

    async def get_calendar(self, calendar_id: str) -> Mapping[str, Any]:
        response = await self._client.request_json("GET", f"/calendar/v4/calendars/{calendar_id}")
        return _unwrap_data(response)

    async def update_calendar(self, calendar_id: str, calendar: Mapping[str, object]) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "PATCH",
            f"/calendar/v4/calendars/{calendar_id}",
            payload=dict(calendar),
        )
        return _unwrap_data(response)

    async def delete_calendar(self, calendar_id: str) -> Mapping[str, Any]:
        response = await self._client.request_json("DELETE", f"/calendar/v4/calendars/{calendar_id}")
        return _unwrap_data(response)

    async def search_calendars(
        self,
        query: str,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"page_size": page_size, "page_token": page_token})
        response = await self._client.request_json(
            "POST",
            "/calendar/v4/calendars/search",
            params=params,
            payload={"query": query},
        )
        return _unwrap_data(response)

    async def create_event(
        self,
        calendar_id: str,
        event: Mapping[str, object],
        *,
        user_id_type: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type, "idempotency_key": idempotency_key})
        response = await self._client.request_json(
            "POST",
            f"/calendar/v4/calendars/{calendar_id}/events",
            params=params,
            payload=dict(event),
        )
        return _unwrap_data(response)

    async def get_event(
        self,
        calendar_id: str,
        event_id: str,
        *,
        need_meeting_settings: Optional[bool] = None,
        need_attendee: Optional[bool] = None,
        max_attendee_num: Optional[int] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "need_meeting_settings": need_meeting_settings,
                "need_attendee": need_attendee,
                "max_attendee_num": max_attendee_num,
                "user_id_type": user_id_type,
            }
        )
        response = await self._client.request_json(
            "GET",
            f"/calendar/v4/calendars/{calendar_id}/events/{event_id}",
            params=params,
        )
        return _unwrap_data(response)

    async def list_events(
        self,
        calendar_id: str,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        sync_token: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        anchor_time: Optional[str] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "page_size": page_size,
                "page_token": page_token,
                "sync_token": sync_token,
                "start_time": start_time,
                "end_time": end_time,
                "anchor_time": anchor_time,
                "user_id_type": user_id_type,
            }
        )
        response = await self._client.request_json(
            "GET",
            f"/calendar/v4/calendars/{calendar_id}/events",
            params=params,
        )
        return _unwrap_data(response)

    async def iter_events(
        self,
        calendar_id: str,
        *,
        page_size: int = 100,
        sync_token: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        anchor_time: Optional[str] = None,
        user_id_type: Optional[str] = None,
    ) -> AsyncIterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = await self.list_events(
                calendar_id,
                page_size=page_size,
                page_token=page_token,
                sync_token=sync_token,
                start_time=start_time,
                end_time=end_time,
                anchor_time=anchor_time,
                user_id_type=user_id_type,
            )
            for item in _iter_page_items(data):
                yield item
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    async def update_event(
        self,
        calendar_id: str,
        event_id: str,
        event: Mapping[str, object],
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        response = await self._client.request_json(
            "PATCH",
            f"/calendar/v4/calendars/{calendar_id}/events/{event_id}",
            params=params,
            payload=dict(event),
        )
        return _unwrap_data(response)

    async def delete_event(
        self,
        calendar_id: str,
        event_id: str,
        *,
        need_notification: Optional[object] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"need_notification": need_notification})
        response = await self._client.request_json(
            "DELETE",
            f"/calendar/v4/calendars/{calendar_id}/events/{event_id}",
            params=params,
        )
        return _unwrap_data(response)

    async def search_events(
        self,
        calendar_id: str,
        query: str,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        user_id_type: Optional[str] = None,
        search_filter: Optional[Mapping[str, object]] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "page_size": page_size,
                "page_token": page_token,
                "user_id_type": user_id_type,
            }
        )
        payload: dict[str, object] = {"query": query}
        if search_filter is not None:
            payload["filter"] = dict(search_filter)
        response = await self._client.request_json(
            "POST",
            f"/calendar/v4/calendars/{calendar_id}/events/search",
            params=params,
            payload=payload,
        )
        return _unwrap_data(response)

    async def reply_event(
        self,
        calendar_id: str,
        event_id: str,
        reply: Mapping[str, object],
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/calendar/v4/calendars/{calendar_id}/events/{event_id}/reply",
            payload=dict(reply),
        )
        return _unwrap_data(response)

    async def list_freebusy(
        self,
        request: Mapping[str, object],
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        response = await self._client.request_json(
            "POST",
            "/calendar/v4/freebusy/list",
            params=params,
            payload=dict(request),
        )
        return _unwrap_data(response)

    async def batch_freebusy(
        self,
        request: Mapping[str, object],
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        response = await self._client.request_json(
            "POST",
            "/calendar/v4/freebusy/batch",
            params=params,
            payload=dict(request),
        )
        return _unwrap_data(response)

    async def generate_caldav_conf(self, request: Mapping[str, object]) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            "/calendar/v4/settings/generate_caldav_conf",
            payload=dict(request),
        )
        return _unwrap_data(response)
