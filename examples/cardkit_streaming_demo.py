"""CardKit streaming + callback demo.

Demonstrates the full CardKit lifecycle:
1. Create a card entity via CardKit API
2. Send it as an interactive message
3. Stream content updates with set_element_content
4. Toggle streaming_mode off when done
5. Handle card.action.trigger with immediate toast + delayed card update

Usage:
    python cardkit_streaming_demo.py

Requires FEISHU_APP_ID, FEISHU_APP_SECRET, and a target chat_id.
"""

import asyncio

from feishu_bot_sdk import (
    AsyncCardKitService,
    AsyncFeishuClient,
    AsyncMessageService,
    CardCallbackResponse,
    FeishuConfig,
    FeishuEventRegistry,
    MessageContent,
    P2CardActionTrigger,
)
from feishu_bot_sdk.webhook import WebhookReceiver

from _settings import load_settings

settings = load_settings()
config = FeishuConfig(
    app_id=settings.app_id,
    app_secret=settings.app_secret,
)

CHAT_ID = "oc_xxx"  # Replace with your chat_id
STREAMING_ELEMENT_ID = "streaming_content"


# ---------------------------------------------------------------------------
# Part 1: CardKit streaming (async)
# ---------------------------------------------------------------------------

CARD_TEMPLATE = {
    "config": {"wide_screen_mode": True},
    "header": {
        "title": {"tag": "plain_text", "content": "Streaming Demo"},
        "template": "blue",
    },
    "elements": [
        {
            "tag": "markdown",
            "element_id": STREAMING_ELEMENT_ID,
            "content": "",
        },
    ],
}


async def demo_streaming() -> None:
    client = AsyncFeishuClient(config)
    cardkit = AsyncCardKitService(client)
    messages = AsyncMessageService(client)

    # 1. Create card entity
    create_resp = cardkit.create(card=CARD_TEMPLATE)
    result = await create_resp
    assert result.ok and result.card_id, f"create failed: {result.msg}"
    card_id = result.card_id
    print(f"card created: {card_id}")

    # 2. Send as interactive message
    content = MessageContent.interactive_card(card_id)
    send_resp = await messages.send(
        receive_id=CHAT_ID,
        receive_id_type="chat_id",
        msg_type="interactive",
        content=content,
    )
    print(f"message sent: {send_resp.message_id}")

    # 3. Enable streaming mode
    await cardkit.set_streaming_mode(card_id, enabled=True, sequence=1)

    # 4. Stream content incrementally
    chunks = ["Hello", "Hello, world!", "Hello, world! This is streaming."]
    for seq, text in enumerate(chunks, start=2):
        await cardkit.set_element_content(
            card_id,
            element_id=STREAMING_ELEMENT_ID,
            content=text,
            sequence=seq,
        )
        await asyncio.sleep(0.5)

    # 5. Close streaming mode
    final_seq = len(chunks) + 2
    await cardkit.set_streaming_mode(card_id, enabled=False, sequence=final_seq)
    print("streaming complete")

    await client.aclose()


# ---------------------------------------------------------------------------
# Part 2: Callback handler (immediate response + delayed update)
# ---------------------------------------------------------------------------

registry = FeishuEventRegistry()


async def _on_card_action(event: P2CardActionTrigger):
    print(f"[card.action.trigger] tag={event.action_tag} value={event.action_value}")
    print(f"  operator: open_id={event.open_id}, union_id={event.union_id}")
    print(f"  context: chat={event.open_chat_id}, msg={event.open_message_id}")

    # Schedule a delayed card update in the background
    asyncio.create_task(_delayed_update(event))

    # Return immediate toast (must respond within 3 seconds)
    return CardCallbackResponse.toast("Processing...", type="info")


async def _delayed_update(event: P2CardActionTrigger):
    """Simulate a slow operation, then update the card via CardKit."""
    await asyncio.sleep(2)
    # In production, you would call cardkit.update() or
    # cardkit.set_element_content() here to push the final result.
    print(f"  delayed update complete for event {event.event_id}")


registry.on_card_action_trigger(_on_card_action)

callback_receiver = WebhookReceiver(
    registry,
    encrypt_key=settings.encrypt_key,
    verification_token=settings.verification_token,
    is_callback=True,
)


if __name__ == "__main__":
    asyncio.run(demo_streaming())
