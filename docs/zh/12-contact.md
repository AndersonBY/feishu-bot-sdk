# 12 通讯录（Contact）

[English](../en/12-contact.md) | [返回中文索引](../README.md)

## 覆盖模块

- `feishu_bot_sdk.contact` -> `ContactService` / `AsyncContactService`

## P0 接口

- 用户：`get_user`、`batch_get_users`、`batch_get_user_ids`、`find_users_by_department`、`search_users`
- 部门：`get_department`、`list_department_children`、`search_departments`、`batch_get_departments`、`list_parent_departments`
- 授权范围：`list_scopes`

## 分页迭代

- 用户：`iter_users_by_department`、`iter_search_users`
- 部门：`iter_department_children`、`iter_search_departments`、`iter_parent_departments`
- 范围：`iter_scopes`（按 `scope_type/scope_id` 逐项返回）

## 快速示例

```python
from feishu_bot_sdk import FeishuClient, FeishuConfig, ContactService

client = FeishuClient(FeishuConfig(app_id="cli_xxx", app_secret="xxx"))
contact = ContactService(client)

user = contact.get_user("ou_xxx", user_id_type="open_id")
print(user.user.name)

dept_users = contact.find_users_by_department("od_xxx", page_size=20)
print(dept_users.items)

for item in contact.iter_department_children("od_xxx", page_size=50):
    print(item.get("department_id"))
```

## CLI 示例

```bash
# 用户
feishu contact user get --user-id ou_xxx --user-id-type open_id --format json
feishu contact user batch-get --user-id ou_xxx --user-id ou_yyy --format json
feishu contact user get-id --email a@example.com --mobile 13800138000 --format json
feishu contact user by-department --department-id od_xxx --page-size 20 --format json
feishu contact user search --query 张三 --format json

# 部门
feishu contact department get --department-id od_xxx --format json
feishu contact department children --department-id od_xxx --fetch-child true --format json
feishu contact department batch-get --department-id od_xxx --department-id od_yyy --format json
feishu contact department parent --department-id od_xxx --format json
feishu contact department search --query 研发 --format json

# 权限范围
feishu contact scope get --page-size 100 --format json
```

## 注意事项

- `contact user search` 与 `contact department search` 官方要求优先使用 `user_access_token`。
- `batch-get` 命令底层使用重复查询参数（例如 `user_ids`、`department_ids`）。
