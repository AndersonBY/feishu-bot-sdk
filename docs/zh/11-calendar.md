# 11 日历（Calendar）

[English](../en/11-calendar.md) | [返回中文索引](../README.md)

## 覆盖模块

- `feishu_bot_sdk.calendar` -> `CalendarService` / `AsyncCalendarService`

## 快速示例

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
        "summary": "项目评审",
        "description": "Q1 里程碑评审",
        "start_time": {"timestamp": "1735700400"},
        "end_time": {"timestamp": "1735704000"},
    },
)
print(event.event.event_id)
```

## 日历 API

- 主日历与列表：`primary_calendar`、`list_calendars`、`iter_calendars`
- 日历管理：`create_calendar`、`get_calendar`、`update_calendar`、`delete_calendar`、`search_calendars`

## 日程 API

- 日程管理：`create_event`、`get_event`、`list_events`、`iter_events`、`update_event`、`delete_event`
- 日程扩展：`search_events`、`reply_event`

## 忙闲与设置 API

- 忙闲查询：`list_freebusy`、`batch_freebusy`
- 本地同步配置：`generate_caldav_conf`

## CLI 示例

```bash
# 获取主日历
feishu calendar primary --format json

# 查询日历
feishu calendar list-calendars --page-size 50 --format json

# 创建日程（从 JSON 文件读取）
feishu calendar create-event --calendar-id cal_xxx --event-file ./event.json --format json

# 给日程追加会议资料（自动处理正确上传点）
feishu calendar attach-material --calendar-id cal_xxx --event-id evt_xxx --path ./agenda.md --format json

# 查询忙闲
feishu calendar list-freebusy --request-file ./freebusy.json --format json
```

## 异步版

- `AsyncCalendarService` 与同步方法名一致。
- 仅调用方式改为 `await`，`iter_*` 方法为 `async for`。
