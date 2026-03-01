import argparse
import os

from feishu_bot_sdk import FeishuClient, FeishuConfig, MessageService

from _settings import load_settings


def build_client() -> FeishuClient:
    settings = load_settings()
    config = FeishuConfig(
        app_id=settings.app_id,
        app_secret=settings.app_secret,
        base_url=os.getenv("FEISHU_BASE_URL", "https://open.feishu.cn/open-apis"),
    )
    return FeishuClient(config)


def main() -> None:
    parser = argparse.ArgumentParser(description="feishu_bot_sdk advanced IM demo")
    parser.add_argument("--receive-id", required=True, help="Target receiver id")
    parser.add_argument("--receive-id-type", default="open_id", help="open_id/user_id/union_id/chat_id")
    parser.add_argument("--message-id", help="Existing message id to operate on")
    parser.add_argument("--urgent-user-id", help="User id for urgent reminder")
    parser.add_argument("--urgent-user-id-type", default="open_id", help="open_id/user_id/union_id")
    parser.add_argument("--batch-open-id", action="append", default=[], help="Open id for batch send")
    args = parser.parse_args()

    client = build_client()
    message = MessageService(client)

    message_id = args.message_id
    if not message_id:
        sent = message.send_text(
            receive_id_type=args.receive_id_type,
            receive_id=args.receive_id,
            text="Advanced IM demo message",
        )
        message_id = str(sent.message_id or "")
        print(f"sent message: {message_id}")

    if message_id:
        message.add_reaction(message_id, "SMILE")
        message.pin_message(message_id)
        print("reaction + pin done")

        if args.urgent_user_id:
            message.send_urgent_app(
                message_id,
                user_id_list=[args.urgent_user_id],
                user_id_type=args.urgent_user_id_type,
            )
            print("urgent reminder sent")

    if args.batch_open_id:
        batch = message.send_batch_message(
            msg_type="text",
            content={"text": "Batch message from feishu_bot_sdk"},
            open_ids=args.batch_open_id,
        )
        print(f"batch message id: {batch.get('message_id')}")


if __name__ == "__main__":
    main()
