# 07 Event System (Events/Webhook/WS)

[中文](../zh/07-events-webhook-ws.md) | [Back to English Index](../README_EN.md)

## Covered Modules

- `feishu_bot_sdk.events`
- `feishu_bot_sdk.webhook`
- `feishu_bot_sdk.ws`

## Typed Event Registration

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

Built-in typed event models:

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
- `P1CustomizedEvent`

## Received Message Content Parsing

`P2ImMessageReceiveV1` now parses message `content` by `message_type` automatically:

- `event.content`: typed message content object
- `event.content_raw`: original JSON string
- `event.text`: text shortcut for `text` and `hongbao`

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

## Webhook Receiver

```python
from feishu_bot_sdk import FeishuEventRegistry, WebhookReceiver

registry = FeishuEventRegistry()

@registry.on_im_message_receive
def on_message(event):
    return {"msg": "ok"}

receiver = WebhookReceiver(
    registry,
    encrypt_key="encrypt_key",
    verification_token="verification_token",
    is_callback=False,
    verify_signatures=True,
)

# In your web framework, pass headers + raw_body:
# result = receiver.handle(headers, raw_body)
```

Notes:

- URL verification is auto-handled with `{"challenge": ...}`.
- Signature checks validate timestamp and signature when `encrypt_key` is set.
- Encrypted payload handling relies on `pycryptodome` (already in dependencies).

## Long Connection (WebSocket)

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

Related objects:

- `fetch_ws_endpoint` / `fetch_ws_endpoint_async`
- `ReconnectPolicy`
- `HeartbeatConfig`
- `WSDispatcher`

## Idempotency

- `build_idempotency_key(envelope)` (defaults to `event_id`)
- `MemoryIdempotencyStore` / `AsyncMemoryIdempotencyStore`

Use idempotency checks at your webhook/WS entrypoint to prevent duplicate processing.
