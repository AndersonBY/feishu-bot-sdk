# 13 Search

[中文版](../zh/13-search.md) | [Back to English Index](../README_EN.md)

## Module Coverage

- `feishu_bot_sdk.search` -> `SearchService` / `AsyncSearchService`

## P0 APIs

- App search: `search_apps`
- Message search: `search_messages`
- Doc/Wiki search: `search_doc_wiki`

## Pagination Iterators

- Apps: `iter_search_apps`
- Messages: `iter_search_messages`
- Docs/Wiki: `iter_search_doc_wiki` (yields `res_units`)

## Quick Example

```python
from feishu_bot_sdk import FeishuClient, FeishuConfig, SearchService

client = FeishuClient(
    FeishuConfig(
        app_id="cli_xxx",
        app_secret="xxx",
        auth_mode="user",
        user_access_token="u-xxx",
    )
)
search = SearchService(client)

apps = search.search_apps("approval", page_size=10)
print(apps.items)

messages = search.search_messages("incident", chat_type="group_chat", page_size=20)
print(messages.items)

docs = search.search_doc_wiki(
    "weekly report",
    doc_filter={"only_title": True, "doc_types": ["DOCX"]},
    page_size=20,
)
print(docs.res_units)
```

## CLI Examples

```bash
# app search
feishu search app --query "approval" --all --format json

# message search
feishu search message --query "incident" --chat-type group_chat --page-size 20 --all --format json

# doc/wiki search
feishu search doc-wiki --query "weekly report" --doc-filter-json '{"only_title": true}' --all --format json
```

## Notes

- The `search` command group defaults to `auth_mode=user` (override with `--auth-mode tenant` if needed).
- `--all` auto-paginates and returns an aggregated result (`items` or `res_units`).
- Official search APIs typically require `user_access_token` and scopes like `search:app`, `search:message`, and `search:docs:read`.
- For `search doc-wiki`, official docs recommend combining `query` with at least one of `doc_filter` or `wiki_filter`.
