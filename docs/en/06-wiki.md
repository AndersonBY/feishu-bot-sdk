# 06 Wiki

[中文](../zh/06-wiki.md) | [Back to English Index](../README_EN.md)

## Covered Module

- `feishu_bot_sdk.wiki` -> `WikiService` / `AsyncWikiService`

## Quick Example

```python
from feishu_bot_sdk import FeishuClient, FeishuConfig, WikiService

client = FeishuClient(FeishuConfig(app_id="cli_xxx", app_secret="xxx"))
wiki = WikiService(client)

spaces = wiki.list_spaces(page_size=10)
print(spaces.items)

results = wiki.search_nodes("weekly report", page_size=10)
print(results.items)
```

## API Summary

- Spaces: `create_space`, `list_spaces`, `iter_spaces`, `get_space`, `update_space_setting`
- Nodes: `get_node`, `search_nodes`, `iter_search_nodes`, `create_node`, `list_nodes`, `iter_nodes`
- Node movement/copy: `copy_node`, `move_node`, `update_node_title`
- Mount docs into wiki: `move_docs_to_wiki`
- Async task query: `get_task`
- Membership: `list_members`, `iter_members`, `add_member`, `remove_member`

## Common Scenarios

1. Search wiki nodes via `search_nodes`.
2. Traverse spaces and nodes with `iter_spaces` + `iter_nodes`.
3. Manage collaboration using `add_member` / `remove_member`.

## Async Version

- `AsyncWikiService` keeps identical method names.
- Async iterators are exposed for `iter_*` methods.
