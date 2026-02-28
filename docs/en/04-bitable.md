# 04 Bitable

[中文](../zh/04-bitable.md) | [Back to English Index](../README_EN.md)

## Covered Module

- `feishu_bot_sdk.bitable` -> `BitableService` / `AsyncBitableService`

## Quick Example

```python
from feishu_bot_sdk import FeishuClient, FeishuConfig, BitableService

client = FeishuClient(FeishuConfig(app_id="cli_xxx", app_secret="xxx"))
bitable = BitableService(client)

app_token, app_url = bitable.create_from_csv("final.csv", "Task Result", "Result Table")
print(app_token, app_url)

bitable.grant_edit_permission(app_token, "ou_xxx", "open_id")

record = bitable.create_record(app_token, "tbl_xxx", {"Task": "Follow up"})
record_id = record["record"]["record_id"]
bitable.update_record(app_token, "tbl_xxx", record_id, {"Task": "Done"})
loaded = bitable.get_record(app_token, "tbl_xxx", record_id)
print(loaded)
bitable.delete_record(app_token, "tbl_xxx", record_id)
```

## Table APIs

- Query and iterate: `list_tables`, `iter_tables`
- Create: `create_table`, `batch_create_tables`
- Update and delete: `update_table`, `delete_table`, `batch_delete_tables`

## Field APIs

- Query and iterate: `list_fields`, `iter_fields`
- Mutations: `create_field`, `update_field`, `delete_field`

## Record APIs

- Query and iterate: `list_records`, `iter_records`, `get_record`
- Create: `create_record`, `batch_create_records`
- Update: `update_record`, `batch_update_records`
- Delete: `delete_record`, `batch_delete_records`

## Important Parameters

- `user_id_type`: controls user-ID format in record payloads.
- `filter` / `sort` / `field_names`: query controls for records.
- `client_token`: idempotency token for retries.
- `text_field_as_array`: rich-text response style.

## Async Version

- `AsyncBitableService` keeps the same method names.
- `iter_*` methods return async iterators.
