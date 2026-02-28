import asyncio

from feishu_bot_sdk import AsyncLongConnectionClient, FeishuEventRegistry

from _settings import load_settings


def _on_im_message_receive(event):
    print("[im.message.receive_v1]", event.message_id, event.text or event.content)


def _on_bot_menu(event):
    print("[application.bot.menu_v6]", event.event_key)


def _on_card_action(event):
    print("[card.action.trigger]", event.action_tag, event.action_value)
    return {
        "toast": {
            "type": "info",
            "content": "ws callback handled",
        }
    }


def _on_url_preview(event):
    print("[url.preview.get]", event.url, event.preview_token)
    return {"inline": {"title": event.url or "preview"}}


def _on_bitable_record_changed(event):
    print("[drive.file.bitable_record_changed_v1]", event.table_id, len(event.action_list))


def _on_bitable_field_changed(event):
    print("[drive.file.bitable_field_changed_v1]", event.table_id, event.revision)


async def main() -> None:
    settings = load_settings()
    registry = FeishuEventRegistry()
    registry.on_im_message_receive(_on_im_message_receive)
    registry.on_bot_menu(_on_bot_menu)
    registry.on_card_action_trigger(_on_card_action)
    registry.on_url_preview_get(_on_url_preview)
    registry.on_bitable_record_changed(_on_bitable_record_changed)
    registry.on_bitable_field_changed(_on_bitable_field_changed)

    client = AsyncLongConnectionClient(
        app_id=settings.app_id,
        app_secret=settings.app_secret,
        handler_registry=registry,
    )
    print("ws listener started")
    await client.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("stopped")
