import asyncio
from typing import Any

from feishu_bot_sdk import FeishuBotServer

from _settings import load_settings


async def main() -> None:
    settings = load_settings()
    server = FeishuBotServer(
        app_id=settings.app_id,
        app_secret=settings.app_secret,
    )

    @server.on_im_message_receive
    async def handle_message(event: Any) -> None:
        print("[im.message.receive_v1]", event.sender_open_id, event.text)

    @server.on_bot_menu
    def handle_menu(event: Any) -> None:
        print("[application.bot.menu_v6]", event.operator_open_id, event.event_key)

    print("server starting...")
    await server.run_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("stopped")
