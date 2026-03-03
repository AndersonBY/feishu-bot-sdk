# 13 搜索（Search）

[English](../en/13-search.md) | [返回中文索引](../README.md)

## 覆盖模块

- `feishu_bot_sdk.search` -> `SearchService` / `AsyncSearchService`

## P0 接口

- 应用搜索：`search_apps`
- 消息搜索：`search_messages`
- 文档/Wiki 搜索：`search_doc_wiki`

## 分页迭代

- 应用：`iter_search_apps`
- 消息：`iter_search_messages`
- 文档/Wiki：`iter_search_doc_wiki`（返回 `res_units`）

## 快速示例

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

apps = search.search_apps("审批", page_size=10)
print(apps.items)

messages = search.search_messages("故障", chat_type="group_chat", page_size=20)
print(messages.items)

docs = search.search_doc_wiki(
    "项目周报",
    doc_filter={"only_title": True, "doc_types": ["DOCX"]},
    page_size=20,
)
print(docs.res_units)
```

## CLI 示例

```bash
# 应用搜索
feishu search app --query "审批" --all --format json

# 消息搜索
feishu search message --query "故障" --chat-type group_chat --page-size 20 --all --format json

# 文档/Wiki 搜索
feishu search doc-wiki --query "项目周报" --doc-filter-json '{"only_title": true}' --all --format json
```

## 注意事项

- `search` 命令组默认使用 `auth_mode=user`（可显式 `--auth-mode tenant` 覆盖）。
- `--all` 会自动翻页并聚合返回结果（`items` 或 `res_units`）。
- 官方搜索接口通常要求 `user_access_token`，并依赖 `search:app` / `search:message` / `search:docs:read` 等权限。
- `search doc-wiki` 官方说明中，建议 `query` 搭配至少一种 `doc_filter` 或 `wiki_filter` 使用。
