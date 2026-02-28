# 08 FeishuBotServer 长连接服务

[English](../en/08-bot-server.md) | [返回中文索引](../README.md)

## 覆盖模块

- `feishu_bot_sdk.server` -> `FeishuBotServer` / `FeishuBotServerStatus`

## 目标

把“长连接 + 事件注册 + 生命周期管理 + 状态统计”整合成一个对象，业务代码只需要注册回调后启动。

## 最小可运行示例

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

## 回调注册方式

- 强类型：
  - `on_im_message_receive`
  - `on_bot_menu`
  - `on_card_action_trigger`
  - `on_url_preview_get`
  - `on_bitable_record_changed`
  - `on_bitable_field_changed`
  - `on_p1_customized_event`
- 通用：
  - `on_event(event_type, handler)`
  - `on_default(handler)`
- 取消注册：
  - `unregister(event_type)`

同步/异步函数都支持作为回调。

## 生命周期控制

- `await start()` / `await stop()`
- `await wait()`：等待当前运行任务结束
- `await run_forever(handle_signals=True)`：保持常驻，默认处理 `SIGINT`/`SIGTERM`
- `run(handle_signals=True)`：同步入口，内部 `asyncio.run(...)`

## 运行状态

`status()` 返回 `FeishuBotServerStatus`：

- `running`
- `started_at` / `stopped_at`
- `last_event_at` / `last_event_type`
- `total_events`
- `event_counts`
- `last_error`

可用于健康检查、日志采样和监控上报。
