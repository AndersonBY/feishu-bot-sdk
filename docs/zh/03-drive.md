# 03 Drive 文件与权限

[English](../en/03-drive.md) | [返回中文索引](../README.md)

## 覆盖模块

- `feishu_bot_sdk.drive_files` -> `DriveFileService` / `AsyncDriveFileService`
- `feishu_bot_sdk.drive_permissions` -> `DrivePermissionService` / `AsyncDrivePermissionService`

## 快速示例

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
print(uploaded.file_token)

task = drive.create_import_task(
    {
        "file_extension": "csv",
        "file_token": uploaded.file_token,
        "type": "bitable",
        "file_name": "导入结果",
        "point": {"mount_type": 1, "mount_key": "fld_xxx"},
    }
)

# 一般先通过 get_import_task(task.ticket) 轮询完成，再取导入结果资源 token 进行授权
perm.add_member(
    task.token,
    resource_type="bitable",
    member_id="ou_xxx",
    member_id_type="open_id",
    perm="edit",
)
```

## `DriveFileService` API 一览

- 上传下载文件：`upload_file`、`upload_file_bytes`、`download_file`
- 分片上传文件：`upload_prepare`、`upload_part`、`upload_finish`
- 导入导出任务：`create_import_task`、`get_import_task`、`create_export_task`、`get_export_task`、`download_export_file`
- 媒体上传下载：`upload_media`、`upload_media_bytes`、`upload_media_prepare`、`upload_media_part`、`upload_media_finish`、`download_media`
- 媒体临时下载链接：`batch_get_media_tmp_download_urls`

## `DrivePermissionService` API 一览

- 成员管理：`list_members`、`add_member`、`batch_add_members`、`update_member`、`remove_member`
- 便捷授权：`grant_edit_permission`
- 权限检查与 owner 转移：`check_member_permission`、`transfer_owner`
- 公开设置：`get_public_settings`、`update_public_settings`
- 密码：`enable_password`、`refresh_password`、`disable_password`

## 常见参数

- `resource_type`: 推荐使用 `bitable` 或 `docx`。
- `member_id_type`: `open_id` / `user_id` / `union_id`。
- `perm`: 常见 `view` / `edit` / `full_access`。

## 注意事项

- `upload_file`/`upload_media` 的 `checksum` 仅在你显式传入时才会提交，默认不自动补。
- 某些接口（如公开密码、短信/电话加急等）可能受租户策略或应用权限限制，返回业务错误码属平台策略行为。
