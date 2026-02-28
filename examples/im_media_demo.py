import argparse
from pathlib import Path

from feishu_bot_sdk import FeishuConfig, FeishuClient, MediaService, MessageService

from _settings import load_settings


FILE_TYPE_BY_SUFFIX = {
    ".opus": "opus",
    ".mp4": "mp4",
    ".pdf": "pdf",
    ".doc": "doc",
    ".xls": "xls",
    ".ppt": "ppt",
}


def _guess_file_type(file_path: Path) -> str:
    return FILE_TYPE_BY_SUFFIX.get(file_path.suffix.lower(), "stream")


def main() -> None:
    parser = argparse.ArgumentParser(description="IM message/media demo")
    parser.add_argument("--receive-id", required=True, help="Target user or chat id")
    parser.add_argument("--receive-id-type", default="open_id", help="open_id/user_id/union_id/email/chat_id")
    parser.add_argument("--text", default="hello from feishu-bot-sdk")
    parser.add_argument("--image", help="Optional local image path to upload and send")
    parser.add_argument("--file", help="Optional local file path to upload and send")
    args = parser.parse_args()

    settings = load_settings()
    config = FeishuConfig(
        app_id=settings.app_id,
        app_secret=settings.app_secret,
        base_url="https://open.feishu.cn/open-apis",
    )
    client = FeishuClient(config)
    message = MessageService(client)
    media = MediaService(client)

    sent = message.send_text(
        receive_id_type=args.receive_id_type,
        receive_id=args.receive_id,
        text=args.text,
    )
    print(f"text sent: {sent.get('message_id')}")

    if args.image:
        image_path = Path(args.image).resolve()
        image_data = media.upload_image(str(image_path), image_type="message")
        image_key = str(image_data.get("image_key") or "")
        if image_key:
            sent_image = message.send(
                receive_id_type=args.receive_id_type,
                receive_id=args.receive_id,
                msg_type="image",
                content={"image_key": image_key},
            )
            print(f"image sent: {sent_image.get('message_id')}")

    if args.file:
        file_path = Path(args.file).resolve()
        file_data = media.upload_file(
            str(file_path),
            file_type=_guess_file_type(file_path),
        )
        file_key = str(file_data.get("file_key") or "")
        if file_key:
            sent_file = message.send(
                receive_id_type=args.receive_id_type,
                receive_id=args.receive_id,
                msg_type="file",
                content={"file_key": file_key},
            )
            print(f"file sent: {sent_file.get('message_id')}")


if __name__ == "__main__":
    main()
