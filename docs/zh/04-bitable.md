# 04 多维表格（Bitable）

[English](../en/04-bitable.md) | [返回中文索引](../README.md)

## 覆盖包

- `feishu_bot_sdk.bitable` 统一导出：`BitableService` / `AsyncBitableService`
- 包内按职责拆分为 `sync` / `async_` / `_csv` / `_common`
- 日常使用直接从 `feishu_bot_sdk.bitable` 导入即可，不需要记内部文件名

## 快速示例

```python
from feishu_bot_sdk import FeishuClient, FeishuConfig, BitableService

client = FeishuClient(FeishuConfig(app_id="cli_xxx", app_secret="xxx"))
bitable = BitableService(client)

# CSV 导入并自动创建多维表格
app_token, app_url = bitable.create_from_csv("final.csv", "任务结果", "结果表")
print(app_token, app_url)

# 授权给用户
bitable.grant_edit_permission(app_token, "ou_xxx", "open_id")

# 记录 CRUD
record = bitable.create_record(app_token, "tbl_xxx", {"任务": "回访客户"})
record_id = record.record.record_id
bitable.update_record(app_token, "tbl_xxx", record_id, {"任务": "已完成"})
loaded = bitable.get_record(app_token, "tbl_xxx", record_id)
print(loaded)
bitable.delete_record(app_token, "tbl_xxx", record_id)
```

## 表 API

- 查询/遍历：`list_tables`、`iter_tables`
- 创建/批量创建：`create_table`、`batch_create_tables`
- 更新/删除：`update_table`、`delete_table`、`batch_delete_tables`

## 字段 API

- 查询/遍历：`list_fields`、`iter_fields`
- 创建/更新/删除：`create_field`、`update_field`、`delete_field`

## 记录 API

- 查询/遍历：`list_records`、`iter_records`、`get_record`
- 创建/批量创建：`create_record`、`batch_create_records`
- 更新/批量更新：`update_record`、`batch_update_records`
- 删除/批量删除：`delete_record`、`batch_delete_records`

## 关键参数说明

- `user_id_type`: 影响记录中用户字段的返回 ID 类型。
- `filter` / `sort` / `field_names`: 查询记录时控制过滤、排序、字段投影。
- `client_token`: 幂等令牌，建议在重试场景传入。
- `text_field_as_array`: 控制富文本字段返回形态。

## CLI 提示

```bash
# 先查表列表
feishu bitable list-tables --app-token app_xxx --format json

# 如果应用有默认表，或者只有一张表，可省略 --table-id
feishu bitable list-records --app-token app_xxx --all --format json
feishu bitable list-views --app-token app_xxx --format json
```

- `bitable create-record`、`list-records`、`list-views`、`get-view`、`create-view`、`update-view`、`delete-view`、`get-field` 会优先使用显式 `--table-id`
- 如果未传 `--table-id`，CLI 会依次尝试：`default_table_id` -> 表列表里唯一一张表
- `bitable get-app` / `copy-app` 在能唯一确定表时，会补充返回 `data.table_id`
- 如果应用下有多张表且 `default_table_id` 为空，CLI 会提示你先运行 `bitable list-tables`

## 异步版

- `AsyncBitableService` 方法名与同步版一致。
- `iter_*` 返回异步迭代器（`async for`）。
