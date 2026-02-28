import argparse
import asyncio
import os
from pathlib import Path

from feishu_bot_sdk import AsyncBitableService, AsyncDocxService, AsyncFeishuClient, FeishuConfig


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def build_client() -> AsyncFeishuClient:
    config = FeishuConfig(
        app_id=_require_env("FEISHU_APP_ID"),
        app_secret=_require_env("FEISHU_APP_SECRET"),
        base_url=os.getenv("FEISHU_BASE_URL", "https://open.feishu.cn/open-apis"),
        doc_url_prefix=os.getenv("FEISHU_DOC_URL_PREFIX"),
        doc_folder_token=os.getenv("FEISHU_DOC_FOLDER_TOKEN"),
        member_permission=os.getenv("FEISHU_MEMBER_PERMISSION", "edit"),
    )
    return AsyncFeishuClient(config)


async def async_main() -> None:
    parser = argparse.ArgumentParser(description="feishu_bot_sdk async example")
    parser.add_argument("--receive-id", required=True, help="Feishu receive_id (e.g. open_id)")
    parser.add_argument(
        "--receive-id-type",
        default="open_id",
        help="open_id/user_id/union_id (default: open_id)",
    )
    parser.add_argument("--text", default="Hello from feishu-bot-sdk (async)")
    parser.add_argument("--csv", help="Optional CSV file to import as Bitable")
    parser.add_argument("--markdown", help="Optional markdown file to append to Docx")
    args = parser.parse_args()

    client = build_client()
    try:
        await client.send_text_message(args.receive_id, args.receive_id_type, args.text)
        print("Message sent.")

        if args.csv:
            csv_path = str(Path(args.csv).resolve())
            bitable = AsyncBitableService(client)
            app_token, app_url = await bitable.create_from_csv(csv_path, "SDK Async Demo", "Result")
            await bitable.grant_edit_permission(app_token, args.receive_id, args.receive_id_type)
            print(f"Bitable created: {app_url}")

        if args.markdown:
            markdown_text = Path(args.markdown).read_text(encoding="utf-8")
            docx = AsyncDocxService(client)
            doc_id, doc_url = await docx.create_document("SDK Async Docx Demo")
            await docx.append_markdown(doc_id, markdown_text)
            await docx.grant_edit_permission(doc_id, args.receive_id, args.receive_id_type)
            print(f"Docx created: {doc_url or doc_id}")
    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(async_main())
