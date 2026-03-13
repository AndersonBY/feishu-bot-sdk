# 03 Drive Files and Permissions

[中文](../zh/03-drive.md) | [Back to English Index](../README_EN.md)

## Covered Modules

- `feishu_bot_sdk.drive_files` -> `DriveFileService` / `AsyncDriveFileService`
- `feishu_bot_sdk.drive_permissions` -> `DrivePermissionService` / `AsyncDrivePermissionService`

## Quick Example

```python
from feishu_bot_sdk import FeishuClient, FeishuConfig, DriveFileService

client = FeishuClient(FeishuConfig(app_id="cli_xxx", app_secret="xxx"))
drive = DriveFileService(client)

uploaded = drive.upload_file(
    "final.csv",
    parent_type="explorer",
    parent_node="fld_xxx",
)

meta = drive.batch_query_metas(
    [{"doc_token": uploaded["file_token"], "doc_type": "file"}],
    with_url=True,
)
stats = drive.get_file_statistics(uploaded["file_token"], file_type="file")

print(meta)
print(stats)
```

## `DriveFileService` API Summary

- File upload/download: `upload_file`, `upload_file_bytes`, `download_file`
- Multipart upload: `upload_prepare`, `upload_part`, `upload_finish`
- Metadata and analytics:
  - `batch_query_metas`
  - `get_file_statistics`
  - `list_file_view_records`
- File operations:
  - `copy_file`
  - `move_file`
  - `delete_file`
  - `create_shortcut`
- Version APIs:
  - `create_version`
  - `list_versions`
  - `get_version`
  - `delete_version`
- Import/export tasks:
  - `create_import_task`
  - `get_import_task`
  - `create_export_task`
  - `get_export_task`
  - `download_export_file`
- Media upload/download:
  - `upload_media`
  - `upload_media_bytes`
  - `upload_media_prepare`
  - `upload_media_part`
  - `upload_media_finish`
  - `download_media`
  - `batch_get_media_tmp_download_urls`

## `DrivePermissionService` API Summary

- Member management: `list_members`, `add_member`, `batch_add_members`, `update_member`, `remove_member`
- Helper grant: `grant_edit_permission`
- Permission check and owner transfer: `check_member_permission`, `transfer_owner`
- Public settings: `get_public_settings`, `update_public_settings`
- Password controls: `enable_password`, `refresh_password`, `disable_password`

## Common Parameters

- `user_id_type`: typically `open_id` / `user_id` / `union_id`
- `viewer_id_type`: user id type used by view-record APIs
- `type` / `file_type` / `obj_type`: follow the official Drive API resource type
- `resource_type`: permission APIs commonly use `bitable` / `docx`

## Practical Guidance

- Prefer `batch_query_metas` when you need metadata for multiple tokens in one request
- For template-copy workflows, call file APIs first, then apply permission APIs
- Keep document version workflows on `create_version`, `list_versions`, `get_version`, and `delete_version`
- `upload_file` / `upload_media` only send `checksum` when you explicitly provide it
