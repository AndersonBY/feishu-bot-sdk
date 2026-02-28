# 08 FeishuBotServer (Long Connection Service)

[中文](../zh/08-bot-server.md) | [Back to English Index](../README_EN.md)

## Covered Module

- `feishu_bot_sdk.server` -> `FeishuBotServer` / `FeishuBotServerStatus`

## Purpose

`FeishuBotServer` combines long connection setup, event registration, lifecycle control, and runtime stats in one object.

## Minimal Example

```python
from feishu_bot_sdk import FeishuBotServer

server = FeishuBotServer(app_id="cli_xxx", app_secret="xxx")

@server.on_im_message_receive
def on_message(event):
    print("open_id:", event.sender_open_id, "text:", event.text)

@server.on_bot_menu
def on_menu(event):
    print("menu event key:", event.event_key)

server.run()
```

## Handler Registration

- Typed handlers:
  - `on_im_message_receive`
  - `on_bot_menu`
  - `on_card_action_trigger`
  - `on_url_preview_get`
  - `on_bitable_record_changed`
  - `on_bitable_field_changed`
  - `on_p1_customized_event`
- Generic handlers:
  - `on_event(event_type, handler)`
  - `on_default(handler)`
- Unregister:
  - `unregister(event_type)`

Both sync and async functions are supported.

## Lifecycle Methods

- `await start()` / `await stop()`
- `await wait()`
- `await run_forever(handle_signals=True)`
- `run(handle_signals=True)` (sync wrapper)

## Runtime Status

`status()` returns `FeishuBotServerStatus` with:

- `running`
- `started_at` / `stopped_at`
- `last_event_at` / `last_event_type`
- `total_events`
- `event_counts`
- `last_error`

Useful for health checks and operational telemetry.
