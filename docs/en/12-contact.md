# 12 Contact (Address Book)

[中文版](../zh/12-contact.md) | [Back to English Index](../README_EN.md)

## Module Coverage

- `feishu_bot_sdk.contact` -> `ContactService` / `AsyncContactService`

## P0 APIs

- Users: `get_user`, `batch_get_users`, `batch_get_user_ids`, `find_users_by_department`, `search_users`
- Departments: `get_department`, `list_department_children`, `search_departments`, `batch_get_departments`, `list_parent_departments`
- Scope: `list_scopes`

## Pagination Iterators

- Users: `iter_users_by_department`, `iter_search_users`
- Departments: `iter_department_children`, `iter_search_departments`, `iter_parent_departments`
- Scope: `iter_scopes` (yields normalized `scope_type/scope_id` entries)

## Quick Example

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

## CLI Examples

```bash
# users
feishu contact user get --user-id ou_xxx --user-id-type open_id --format json
feishu contact user batch-get --user-id ou_xxx --user-id ou_yyy --format json
feishu contact user get-id --email a@example.com --mobile 13800138000 --format json
feishu contact user by-department --department-id od_xxx --page-size 20 --format json
feishu contact user search --query alice --format json

# departments
feishu contact department get --department-id od_xxx --format json
feishu contact department children --department-id od_xxx --fetch-child true --format json
feishu contact department batch-get --department-id od_xxx --department-id od_yyy --format json
feishu contact department parent --department-id od_xxx --format json
feishu contact department search --query engineering --format json

# scope
feishu contact scope get --page-size 100 --format json
```

## Notes

- `contact user search` and `contact department search` should use `user_access_token` per official docs.
- `batch-get` commands use repeated query keys (`user_ids`, `department_ids`) under the hood.
