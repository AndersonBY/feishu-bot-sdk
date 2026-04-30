# 06 Wiki 知识库

[English](../en/06-wiki.md) | [返回中文索引](../README.md)

## 覆盖模块

- `feishu_bot_sdk.wiki` -> `WikiService` / `AsyncWikiService`

## 快速示例

```python
from feishu_bot_sdk import FeishuClient, FeishuConfig, WikiService

client = FeishuClient(FeishuConfig(app_id="cli_xxx", app_secret="xxx"))
wiki = WikiService(client)

spaces = wiki.list_spaces(page_size=10)
print(spaces.items)

results = wiki.search_nodes("项目周报", page_size=10)
print(results.items)
```

## API 一览

- 空间：`create_space`、`list_spaces`、`iter_spaces`、`get_space`、`update_space_setting`
- 节点：`get_node`、`search_nodes`、`iter_search_nodes`、`create_node`、`list_nodes`、`iter_nodes`
- 节点移动复制：`copy_node`、`move_node`、`update_node_title`
- 文档挂载到 wiki：`move_docs_to_wiki`
- 异步任务查询：`get_task`
- 成员管理：`list_members`、`iter_members`、`add_member`、`remove_member`

## 常用场景

1. 搜索 wiki 节点：`search_nodes`。
2. 批量遍历全空间：`iter_spaces` + `iter_nodes`。
3. 协作权限管理：`add_member` / `remove_member`。

## 异步版

- `AsyncWikiService` 方法名一致，异步遍历接口返回 `AsyncIterator`。

## lark-cli Shortcut 示例

```bash
feishu wiki +node-create --space-id spc_xxx --parent-node-token wiki_xxx --title "Runbook" --format json
feishu wiki +move --node-token wiki_xxx --source-space-id spc_xxx --target-space-id spc_xxx --target-parent-token wiki_parent --format json
feishu wiki +delete-space --space-id spc_xxx --format json
```
