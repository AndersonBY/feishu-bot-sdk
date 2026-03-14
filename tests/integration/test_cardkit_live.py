"""Live integration test for CardKit APIs.

Reads credentials from the root .env and exercises:
1. CardKitService.create  → get card_id
2. CardKitService.set_streaming_mode(enabled=True)
3. CardKitService.set_element_content  (3 incremental chunks)
4. CardKitService.set_streaming_mode(enabled=False)
5. CardKitService.update  (final card with header change)

Also verifies CardCallbackResponse helpers produce valid dicts.
"""

import sys, os, time

_examples_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "examples")
sys.path.insert(0, _examples_dir)

from _settings import load_settings
from feishu_bot_sdk import (
    CardKitService,
    CardKitCreateResponse,
    CardKitResponse,
    CardCallbackResponse,
    FeishuClient,
    FeishuConfig,
)

settings = load_settings()
config = FeishuConfig(
    app_id=settings.app_id,
    app_secret=settings.app_secret,
)
client = FeishuClient(config)
cardkit = CardKitService(client)

STREAMING_ELEMENT_ID = "streaming_el"

CARD_JSON = {
    "schema": "2.0",
    "config": {
        "wide_screen_mode": True,
        "streaming_mode": True,
    },
    "header": {
        "title": {"tag": "plain_text", "content": "CardKit Live Test"},
        "template": "blue",
    },
    "body": {
        "elements": [
            {
                "tag": "markdown",
                "element_id": STREAMING_ELEMENT_ID,
                "content": "",
            },
        ],
    },
}


def main():
    print("=" * 60)
    print("CardKit Live Integration Test")
    print("=" * 60)

    # --- 1. Create card entity ---
    print("\n[1] Creating card entity...")
    create_resp = cardkit.create(card=CARD_JSON)
    print(f"    code={create_resp.code}, msg={create_resp.msg}")
    print(f"    card_id={create_resp.card_id}")
    assert create_resp.ok, f"create failed: {create_resp.msg}"
    assert create_resp.card_id, "card_id is empty"
    card_id = create_resp.card_id
    print(f"    ✓ Card created: {card_id}")

    # --- 2. Enable streaming mode ---
    print("\n[2] Enabling streaming mode...")
    resp = cardkit.set_streaming_mode(card_id, enabled=True, sequence=1)
    print(f"    code={resp.code}, msg={resp.msg}")
    assert resp.ok, f"set_streaming_mode(True) failed: {resp.msg}"
    print("    ✓ Streaming mode enabled")

    # --- 3. Stream content ---
    print("\n[3] Streaming content (3 chunks)...")
    chunks = [
        "Hello",
        "Hello, world!",
        "Hello, world! CardKit streaming works. 🎉",
    ]
    for i, text in enumerate(chunks, start=2):
        resp = cardkit.set_element_content(
            card_id,
            element_id=STREAMING_ELEMENT_ID,
            content=text,
            sequence=i,
        )
        print(f"    seq={i}: code={resp.code}, content_len={len(text)}")
        assert resp.ok, f"set_element_content seq={i} failed: {resp.msg}"
        time.sleep(0.3)
    print("    ✓ All chunks streamed")

    # --- 4. Disable streaming mode ---
    next_seq = len(chunks) + 2
    print(f"\n[4] Disabling streaming mode (seq={next_seq})...")
    resp = cardkit.set_streaming_mode(card_id, enabled=False, sequence=next_seq)
    print(f"    code={resp.code}, msg={resp.msg}")
    assert resp.ok, f"set_streaming_mode(False) failed: {resp.msg}"
    print("    ✓ Streaming mode disabled")

    # --- 5. Full card update ---
    next_seq += 1
    print(f"\n[5] Updating full card (seq={next_seq})...")
    final_card = {
        "schema": "2.0",
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": "CardKit Test Complete"},
            "template": "green",
        },
        "body": {
            "elements": [
                {
                    "tag": "markdown",
                    "element_id": STREAMING_ELEMENT_ID,
                    "content": "**Done!** All CardKit APIs verified.",
                },
            ],
        },
    }
    resp = cardkit.update(card_id, card=final_card, sequence=next_seq)
    print(f"    code={resp.code}, msg={resp.msg}")
    assert resp.ok, f"update failed: {resp.msg}"
    print("    ✓ Card updated to final state")

    # --- 6. Verify CardCallbackResponse helpers ---
    print("\n[6] Verifying CardCallbackResponse helpers...")
    toast = CardCallbackResponse.toast("OK", type="success")
    assert toast["toast"]["type"] == "success"
    card_resp = CardCallbackResponse.card({"elements": []})
    assert "card" in card_resp
    inline = CardCallbackResponse.inline(toast={"type": "info"})
    assert inline["toast"]["type"] == "info"
    print("    ✓ All callback helpers produce valid dicts")

    print("\n" + "=" * 60)
    print(f"ALL PASSED — card_id: {card_id}")
    print("=" * 60)


if __name__ == "__main__":
    main()
