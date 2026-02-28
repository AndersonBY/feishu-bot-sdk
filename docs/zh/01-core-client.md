# 01 核心客户端与配置

[English](../en/01-core-client.md) | [返回中文索引](../README.md)

## 覆盖模块

- `feishu_bot_sdk.config` -> `FeishuConfig`
- `feishu_bot_sdk.feishu` -> `FeishuClient` / `AsyncFeishuClient`

## 最小初始化

```python
from feishu_bot_sdk import FeishuClient, FeishuConfig

config = FeishuConfig(
    app_id="cli_xxx",
    app_secret="xxx",
)
client = FeishuClient(config)
```

异步版本：

```python
from feishu_bot_sdk import AsyncFeishuClient, FeishuConfig

config = FeishuConfig(app_id="cli_xxx", app_secret="xxx")
client = AsyncFeishuClient(config)

# 使用完成后关闭连接池
await client.aclose()
```

## `FeishuConfig` 字段说明

- `app_id` / `app_secret`: 飞书应用凭证。
- `base_url`: 默认 `https://open.feishu.cn/open-apis`。
- `tenant_access_token`: 可选，手动注入 token（不走 app_id/app_secret 换取）。
- `doc_url_prefix`: 构造文档链接时使用，例如 `https://<tenant>.feishu.cn/docx`。
- `doc_folder_token`: Docx 创建默认目录。
- `member_permission`: 授权默认权限（常用 `edit`）。
- `timeout_seconds`: HTTP 超时时间。
- `rate_limit_enabled`: 是否开启自适应限流。
- `rate_limit_*`: 限流参数（QPS、收敛/恢复因子、冷却时间、最大等待等）。

## 客户端能力

`FeishuClient` 与 `AsyncFeishuClient` 都支持：

- `get_tenant_access_token()`: 获取并缓存 tenant token。
- `send_text_message(receive_id, receive_id_type, text)`: 快速发送文本消息。
- `request_json(method, path, payload=None, params=None)`: 通用 API 调用入口。

## 通用请求示例

```python
resp = client.request_json(
    "GET",
    "/im/v1/messages/om_xxx",
    params={"user_id_type": "open_id"},
)
print(resp)
```

## 建议实践

- 业务层优先使用各服务对象（`MessageService`、`BitableService` 等），仅在 SDK 尚未封装的接口使用 `request_json`。
- 异步项目统一使用 `Async*` 系列，避免同步阻塞。
- 长连接服务中不要重复创建客户端实例，复用单例配置。
