# 11 Calendar

[中文](../zh/11-calendar.md) | [Back to English Index](../README_EN.md)

## Covered Module

- `feishu_bot_sdk.calendar` -> `CalendarService` / `AsyncCalendarService`

## Quick Example

```python
from feishu_bot_sdk import FeishuClient, FeishuConfig, CalendarService

client = FeishuClient(FeishuConfig(app_id="cli_xxx", app_secret="xxx"))
calendar = CalendarService(client)

primary = calendar.primary_calendar()
calendar_id = primary.calendar.calendar_id
print(calendar_id)

event = calendar.create_event(
    calendar_id,
    {
        "summary": "Project Review",
        "description": "Q1 milestone review",
        "start_time": {"timestamp": "1735700400"},
        "end_time": {"timestamp": "1735704000"},
    },
)
print(event.event.event_id)
```

## Calendar APIs

- Primary and listing: `primary_calendar`, `list_calendars`, `iter_calendars`
- Calendar management: `create_calendar`, `get_calendar`, `update_calendar`, `delete_calendar`, `search_calendars`

## Event APIs

- Event management: `create_event`, `get_event`, `list_events`, `iter_events`, `update_event`, `delete_event`
- Event extensions: `search_events`, `reply_event`

## Freebusy and Settings APIs

- Freebusy: `list_freebusy`, `batch_freebusy`
- Local calendar sync config: `generate_caldav_conf`

## CLI Examples

```bash
# get primary calendar
feishu calendar primary --format json

# list calendars
feishu calendar list-calendars --page-size 50 --format json

# create event from JSON file
feishu calendar create-event --calendar-id cal_xxx --event-file ./event.json --format json

# attach meeting material to an event (uses correct upload point automatically)
feishu calendar attach-material --calendar-id cal_xxx --event-id evt_xxx --path ./agenda.md --format json

# query freebusy
feishu calendar list-freebusy --request-file ./freebusy.json --format json
```

## Async Version

- `AsyncCalendarService` keeps the same method names.
- Call methods with `await`; use `async for` for `iter_*` methods.
