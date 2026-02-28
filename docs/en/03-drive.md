# 03 Drive Files and Permissions

[中文](../zh/03-drive.md) | [Back to English Index](../README_EN.md)

## Covered Modules

- `feishu_bot_sdk.drive_files` -> `DriveFileService` / `AsyncDriveFileService`
- `feishu_bot_sdk.drive_permissions` -> `DrivePermissionService` / `AsyncDrivePermissionService`

## Quick Example

```python
from feishu_bot_sdk import FeishuClient, FeishuConfig, DriveFileService, DrivePermissionService

client = FeishuClient(FeishuConfig(app_id="cli_xxx", app_secret="xxx"))
drive = DriveFileService(client)
perm = DrivePermissionService(client)

uploaded = drive.upload_file(
    "final.csv",
    parent_type="explorer",
    parent_node="fld_xxx",
)

task = drive.create_import_task(
    {
        "file_extension": "csv",
        "file_token": uploaded["file_token"],
        "type": "bitable",
        "file_name": "Import Result",
        "point": {"mount_type": 1, "mount_key": "fld_xxx"},
    }
)

perm.add_member(
    task["token"],
    resource_type="bitable",
    member_id="ou_xxx",
    member_id_type="open_id",
    perm="edit",
)
```

## `DriveFileService` API Summary

- File upload/download: `upload_file`, `upload_file_bytes`, `download_file`
- Multipart upload: `upload_prepare`, `upload_part`, `upload_finish`
- Import/export tasks: `create_import_task`, `get_import_task`, `create_export_task`, `get_export_task`, `download_export_file`
- Media upload/download: `upload_media`, `upload_media_bytes`, `upload_media_prepare`, `upload_media_part`, `upload_media_finish`, `download_media`
- Temp media URLs: `batch_get_media_tmp_download_urls`

## `DrivePermissionService` API Summary

- Member management: `list_members`, `add_member`, `batch_add_members`, `update_member`, `remove_member`
- Helper grant: `grant_edit_permission`
- Permission check and owner transfer: `check_member_permission`, `transfer_owner`
- Public settings: `get_public_settings`, `update_public_settings`
- Password controls: `enable_password`, `refresh_password`, `disable_password`

## Common Parameters

- `resource_type`: usually `bitable` or `docx`.
- `member_id_type`: `open_id` / `user_id` / `union_id`.
- `perm`: commonly `view` / `edit` / `full_access`.

## Notes

- `upload_file`/`upload_media` only send `checksum` when explicitly provided.
- Some APIs are tenant-policy dependent and may return business errors even with valid SDK calls.
