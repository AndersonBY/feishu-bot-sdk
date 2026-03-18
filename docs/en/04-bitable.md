# 04 Bitable

[中文](../zh/04-bitable.md) | [Back to English Index](../README_EN.md)

## Covered Package

- `feishu_bot_sdk.bitable` re-exports `BitableService` / `AsyncBitableService`
- Internally the package is organized as `sync` / `async_` / `_csv` / `_common`
- For normal usage, import from `feishu_bot_sdk.bitable` and ignore the internal file layout

## Quick Example

```python
from feishu_bot_sdk import FeishuClient, FeishuConfig, BitableService

client = FeishuClient(FeishuConfig(app_id="cli_xxx", app_secret="xxx"))
bitable = BitableService(client)

app_token, app_url = bitable.create_from_csv("final.csv", "Task Result", "Result Table")
print(app_token, app_url)

bitable.grant_edit_permission(app_token, "ou_xxx", "open_id")

record = bitable.create_record(app_token, "tbl_xxx", {"Task": "Follow up"})
record_id = record.record.record_id
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

## CLI Notes

```bash
# Inspect tables first
feishu bitable list-tables --app-token app_xxx --format json

# When the app has a default table or exactly one table, --table-id can be omitted
feishu bitable list-records --app-token app_xxx --all --format json
feishu bitable list-views --app-token app_xxx --format json
```

- `bitable create-record`, `list-records`, `list-views`, `get-view`, `create-view`, `update-view`, `delete-view`, and `get-field` prefer an explicit `--table-id`
- If `--table-id` is omitted, the CLI tries `default_table_id` first, then auto-selects the only table when the app has exactly one table
- `bitable get-app` and `copy-app` backfill `data.table_id` when the table can be resolved uniquely
- If the app has multiple tables and no default table ID, the CLI will tell you to run `bitable list-tables`

## Async Version

- `AsyncBitableService` keeps the same method names.
- `iter_*` methods return async iterators.
