# 01 Core Client and Config

[中文](../zh/01-core-client.md) | [Back to English Index](../README_EN.md)

## Covered Modules

- `feishu_bot_sdk.config` -> `FeishuConfig`
- `feishu_bot_sdk.feishu` -> `FeishuClient` / `AsyncFeishuClient`

## Minimal Setup

```python
from feishu_bot_sdk import FeishuClient, FeishuConfig

config = FeishuConfig(
    app_id="cli_xxx",
    app_secret="xxx",
)
client = FeishuClient(config)
```

Async version:

```python
from feishu_bot_sdk import AsyncFeishuClient, FeishuConfig

config = FeishuConfig(app_id="cli_xxx", app_secret="xxx")
client = AsyncFeishuClient(config)

await client.aclose()
```

## `FeishuConfig` Fields

- `app_id` / `app_secret`: app credentials.
- `base_url`: default is `https://open.feishu.cn/open-apis`.
- `auth_mode`: `tenant` or `user` (default: `tenant`).
- `access_token`: optional static access token for current `auth_mode`.
- `app_access_token`: optional app token for OAuth token exchange endpoints.
- `user_access_token`: optional user access token.
- `user_refresh_token`: optional user refresh token for auto refresh.
- `doc_url_prefix`: used when generating doc URLs.
- `doc_folder_token`: default folder for doc creation.
- `member_permission`: default permission for grant helpers (commonly `edit`).
- `timeout_seconds`: HTTP timeout.
- `rate_limit_enabled`: whether adaptive rate limit is enabled.
- `rate_limit_*`: adaptive rate limit tuning values.

## Client Methods

Both `FeishuClient` and `AsyncFeishuClient` provide:

- `get_access_token()`
- `get_app_access_token()`
- `build_authorize_url()`
- `exchange_authorization_code()`
- `refresh_user_access_token()`
- `get_user_info()`
- `send_text_message(receive_id, receive_id_type, text)`
- `request_json(method, path, payload=None, params=None)`

## Recommended Auth Modes

Tenant mode (typical bot backend):

```python
config = FeishuConfig(
    app_id="cli_xxx",
    app_secret="xxx",
    auth_mode="tenant",
)
```

User mode (typical OAuth workflow):

```python
config = FeishuConfig(
    app_id="cli_xxx",
    app_secret="xxx",
    auth_mode="user",
    user_access_token="u-xxx",
    user_refresh_token="r-xxx",
)
```

## Generic Request Example

```python
resp = client.request_json(
    "GET",
    "/im/v1/messages/om_xxx",
    params={"user_id_type": "open_id"},
)
print(resp)
```

## Recommended Usage

- Prefer higher-level services (`MessageService`, `BitableService`, etc.) for stable APIs.
- Use `request_json` only for unsupported endpoints.
- In async projects, keep all calls in the `Async*` family.
