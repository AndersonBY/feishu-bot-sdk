# Event Handling Reference

## FeishuBotServer (Recommended)

Turnkey server combining WebSocket connection with event dispatching:

```python
from feishu_bot_sdk import FeishuBotServer

server = FeishuBotServer(
    app_id="cli_xxx",
    app_secret="xxx",
    domain="https://open.feishu.cn",  # default
    timeout_seconds=30.0,
)

@server.on_im_message_receive
def handle_message(event):
    # event.text, event.sender_open_id, event.chat_id, event.message_id, etc.
    print(f"Message: {event.text}")

@server.on_bot_menu
def handle_menu(event):
    # event.event_key, event.operator_open_id
    print(f"Menu: {event.event_key}")

@server.on_card_action_trigger
def handle_card(event):
    # Return dict for card callback response
    return {"toast": {"type": "info", "content": "Done"}}

@server.on_bitable_record_changed
def handle_bitable(event):
    print(f"Table: {event.table_id}, changes: {len(event.action_list)}")

# Blocking run (handles SIGINT/SIGTERM)
server.run()

# Or async control
await server.start()
status = server.status()  # FeishuBotServerStatus
await server.stop()
```

## FeishuEventRegistry (Custom Setup)

For custom integration without FeishuBotServer:

```python
from feishu_bot_sdk import FeishuEventRegistry

registry = FeishuEventRegistry()

@registry.on_im_message_receive
def handle_message(event):
    print(event.text)

@registry.on_bot_menu
def handle_menu(event):
    print(event.event_key)

@registry.on_card_action_trigger
def handle_card(event):
    return {"toast": {"type": "info", "content": "OK"}}

@registry.on_bitable_record_changed
def handle_bitable(event):
    pass

@registry.on_bitable_field_changed
def handle_field(event):
    pass

@registry.on_url_preview_get
def handle_preview(event):
    pass
```

## WebhookReceiver (HTTP Webhook)

For receiving events via HTTP webhook endpoint:

```python
from feishu_bot_sdk import WebhookReceiver
import json

receiver = WebhookReceiver(
    registry=registry,
    encrypt_key="your_encrypt_key",
    verification_token="your_verify_token",
    is_callback=False,  # False for event subscriptions, True for card callbacks
)

# In your HTTP handler (Flask/FastAPI/etc.)
def handle_webhook(request):
    payload = receiver.handle(dict(request.headers), request.body)
    return json.dumps(payload)
```

### Webhook Utilities

```python
from feishu_bot_sdk.webhook import (
    verify_signature,
    verify_timestamp,
    decode_webhook_body,
    build_challenge_response,
)

# Verify incoming webhook
verify_signature(headers, body, encrypt_key, timestamp_tolerance_seconds=300)

# Challenge-response for webhook URL verification
response = build_challenge_response(challenge="xxx", encrypt_key="key")
```

## LongConnectionClient (WebSocket)

For direct WebSocket event streaming:

```python
from feishu_bot_sdk import LongConnectionClient

ws_client = LongConnectionClient(
    app_id="cli_xxx",
    app_secret="xxx",
    registry=registry,
)

# Run (async)
await ws_client.start()
# ... events dispatched to registry handlers ...
await ws_client.stop()
```

## Event Models

| Decorator | Event Type | Key Fields |
|-----------|-----------|------------|
| `on_im_message_receive` | `im.message.receive_v1` | `text`, `sender_open_id`, `chat_id`, `message_id`, `msg_type` |
| `on_bot_menu` | `application.bot.menu_v6` | `event_key`, `operator_open_id` |
| `on_card_action_trigger` | `card.action.trigger` | Card action payload; return dict for response |
| `on_bitable_record_changed` | `drive.file.bitable_record_changed_v1` | `table_id`, `action_list` |
| `on_bitable_field_changed` | `drive.file.bitable_field_changed_v1` | Field change details |
| `on_url_preview_get` | `url.preview.get` | URL preview request |
