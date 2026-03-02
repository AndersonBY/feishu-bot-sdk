# 07 事件系统（Events/Webhook/WS）

[English](../en/07-events-webhook-ws.md) | [返回中文索引](../README.md)

## 覆盖模块

- `feishu_bot_sdk.events`
- `feishu_bot_sdk.webhook`
- `feishu_bot_sdk.ws`

## 事件注册（强类型）

```python
from feishu_bot_sdk import FeishuEventRegistry

registry = FeishuEventRegistry()

@registry.on_im_message_receive
def on_message(event):
    print(event.sender_open_id, event.text)

@registry.on_bot_menu
def on_menu(event):
    print(event.event_key)
```

已内置的强类型事件模型：

- `P2ImMessageReceiveV1`
- `P2ImMessageReadV1`
- `P2ImMessageRecalledV1`
- `P2ImMessageReactionCreatedV1`
- `P2ImMessageReactionDeletedV1`
- `P2ApplicationBotMenuV6`
- `P2CardActionTrigger`
- `P2URLPreviewGet`
- `P2DriveFileBitableRecordChangedV1`
- `P2DriveFileBitableFieldChangedV1`
- `P1CustomizedEvent`（自定义事件）

## 接收消息内容解析

`P2ImMessageReceiveV1` 现在会自动按 `message_type` 解析 `content`，并提供：

- `event.content`: 强类型消息内容对象
- `event.content_raw`: 原始 JSON 字符串
- `event.text`: 文本类消息快捷字段（`text`/`hongbao`）

```python
from feishu_bot_sdk import (
    FeishuEventRegistry,
    TextMessageContent,
    ImageMessageContent,
    FileMessageContent,
)

registry = FeishuEventRegistry()

@registry.on_im_message_receive
def on_message(event):
    if isinstance(event.content, TextMessageContent):
        print("text:", event.content.text)
    elif isinstance(event.content, ImageMessageContent):
        print("image_key:", event.content.image_key)
    elif isinstance(event.content, FileMessageContent):
        print("file:", event.content.file_name, event.content.file_key)
    else:
        print("raw:", event.content_raw)
```

## Webhook 接收

```python
from feishu_bot_sdk import FeishuEventRegistry, WebhookReceiver

registry = FeishuEventRegistry()

@registry.on_im_message_receive
def on_message(event):
    return {"msg": "ok"}

receiver = WebhookReceiver(
    registry,
    encrypt_key="encrypt_key",               # 可选：加密回调需要
    verification_token="verification_token", # 可选：校验 token
    is_callback=False,                       # 卡片回调可设 True
    verify_signatures=True,
)

# 在你的 Web 框架里传入 headers + raw_body
# result = receiver.handle(headers, raw_body)
```

关键点：

- URL 验证请求会自动返回 `{"challenge": ...}`。
- 如果启用签名校验且传了 `encrypt_key`，会校验时间戳与签名。
- 加密回调依赖 `pycryptodome`（SDK 依赖已包含）。

## 长连接（WebSocket）接收

```python
import asyncio
from feishu_bot_sdk import AsyncLongConnectionClient, FeishuEventRegistry

registry = FeishuEventRegistry()

@registry.on_im_message_receive
def on_message(event):
    print("text:", event.text)

client = AsyncLongConnectionClient(
    app_id="cli_xxx",
    app_secret="xxx",
    handler_registry=registry,
)

asyncio.run(client.start())
```

相关对象：

- `fetch_ws_endpoint` / `fetch_ws_endpoint_async`: 获取长连接 endpoint。
- `ReconnectPolicy`: 重连次数、间隔、首次抖动。
- `HeartbeatConfig`: 心跳间隔配置。
- `WSDispatcher`: 帧负载转事件并分发。

## 去重能力（幂等）

- `build_idempotency_key(envelope)`: 默认使用 `event_id`。
- `MemoryIdempotencyStore` / `AsyncMemoryIdempotencyStore`: 内存级 TTL 去重。

建议在 webhook/长连接入口处做去重，避免重复消费。
