import argparse
import asyncio

from feishu_bot_sdk import AsyncDocContentService, AsyncFeishuClient, AsyncWikiService, FeishuConfig

from _settings import load_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Wiki and docs content demo")
    parser.add_argument("--search-keyword", default="", help="keyword for wiki search")
    parser.add_argument("--search-space-id", default="", help="optional wiki space_id for search")
    parser.add_argument("--doc-token", default="", help="doc token used by docs/v1/content")
    parser.add_argument("--doc-type", default="docx", help="doc type, default: docx")
    parser.add_argument("--lang", default="", help="optional language for markdown export")
    parser.add_argument("--preview-chars", type=int, default=300, help="preview size for markdown")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    settings = load_settings()
    client = AsyncFeishuClient(FeishuConfig(app_id=settings.app_id, app_secret=settings.app_secret))
    wiki = AsyncWikiService(client)
    docs = AsyncDocContentService(client)

    spaces = await wiki.list_spaces(page_size=5)
    space_items = spaces.get("items", [])
    print(f"[wiki] spaces fetched: {len(space_items) if isinstance(space_items, list) else 0}")

    if args.search_keyword:
        results = await wiki.search_nodes(
            args.search_keyword,
            space_id=args.search_space_id or None,
            page_size=10,
        )
        items = results.get("items", [])
        print(f"[wiki] search hits: {len(items) if isinstance(items, list) else 0}")
        if isinstance(items, list) and items:
            first = items[0]
            print("[wiki] first hit:", first.get("title"), first.get("node_id"), first.get("obj_token"))

    if args.doc_token:
        markdown = await docs.get_markdown(
            args.doc_token,
            doc_type=args.doc_type,
            lang=args.lang or None,
        )
        preview = markdown[: max(args.preview_chars, 0)]
        print("[docs] markdown preview:")
        print(preview)

    await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
