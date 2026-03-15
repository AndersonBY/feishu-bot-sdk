# 03 Drive 文件与权限

[English](../en/03-drive.md) | [返回中文索引](../README.md)

## 覆盖包

- `feishu_bot_sdk.drive` 统一导出：
  `DriveFileService` / `AsyncDriveFileService`、
  `DrivePermissionService` / `AsyncDrivePermissionService`
- 包内按职责拆分为 `files` / `permissions`
- 日常使用建议直接从 `feishu_bot_sdk.drive` 导入，不需要记内部文件名

## 快速示例

```python
from feishu_bot_sdk import FeishuClient, FeishuConfig
from feishu_bot_sdk.drive import DriveFileService

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

## `DriveFileService` API 一览

- 文件上传下载：`upload_file`、`upload_file_bytes`、`download_file`
- 分片上传：`upload_prepare`、`upload_part`、`upload_finish`
- 文件元数据与统计：
  - `batch_query_metas`
  - `get_file_statistics`
  - `list_file_view_records`
- 文件操作：
  - `copy_file`
  - `move_file`
  - `delete_file`
  - `create_shortcut`
- 文档版本：
  - `create_version`
  - `list_versions`
  - `get_version`
  - `delete_version`
- 导入导出任务：
  - `create_import_task`
  - `get_import_task`
  - `create_export_task`
  - `get_export_task`
  - `download_export_file`
- 媒体上传下载：
  - `upload_media`
  - `upload_media_bytes`
  - `upload_media_prepare`
  - `upload_media_part`
  - `upload_media_finish`
  - `download_media`
  - `batch_get_media_tmp_download_urls`

## `DrivePermissionService` API 一览

- 成员管理：`list_members`、`add_member`、`batch_add_members`、`update_member`、`remove_member`
- 便捷授权：`grant_edit_permission`
- 权限检查与 owner 转移：`check_member_permission`、`transfer_owner`
- 公开设置：`get_public_settings`、`update_public_settings`
- 密码：`enable_password`、`refresh_password`、`disable_password`

## 常见参数

- `user_id_type`：常见 `open_id` / `user_id` / `union_id`
- `viewer_id_type`：访问记录接口使用的用户 ID 类型
- `type` / `file_type` / `obj_type`：按飞书官方接口要求填写资源类型
- `resource_type`：权限接口常用 `bitable` / `docx`

## 实践建议

- 元数据查询优先用 `batch_query_metas`，便于一次查多个 token
- 做“复制模板 -> 移动 -> 授权”这类流程时，先调用文件接口，再补权限接口
- 版本管理场景统一走 `create_version` / `list_versions` / `get_version` / `delete_version`
- `upload_file` / `upload_media` 只有在显式传入 `checksum` 时才会提交校验值
