# 09 类型、异常与限流

[English](../en/09-types-errors-rate-limit.md) | [返回中文索引](../README.md)

## 覆盖模块

- `feishu_bot_sdk.types`
- `feishu_bot_sdk.exceptions`
- `feishu_bot_sdk.rate_limit`

## 常用枚举（`types`）

- `MemberIdType`: `open_id` / `user_id` / `union_id`
- `Permission`: `view` / `edit` / `full_access`
- `DriveResourceType`: `bitable` / `docx`

这些类型可以直接替代字符串字面量，减少拼写错误。

## 异常体系（`exceptions`）

- `SDKError`: SDK 基础异常
- `ConfigurationError`: 配置错误
- `HTTPRequestError`: HTTP 层失败，可读取：
  - `status_code`
  - `response_text`
  - `response_headers`
- `FeishuError`: 飞书业务错误（如 `code != 0`）

示例：

```python
from feishu_bot_sdk import FeishuError, HTTPRequestError

try:
    ...
except FeishuError as exc:
    print("feishu error:", exc)
except HTTPRequestError as exc:
    print(exc.status_code, exc.response_text)
```

## 自适应限流（`rate_limit`）

对象：

- `RateLimitTuning`
- `AdaptiveRateLimiter`
- `AsyncAdaptiveRateLimiter`
- `build_rate_limit_key(method, path)`

`FeishuClient` 默认启用自适应限流，你通常只需要在 `FeishuConfig` 里调参：

```python
from feishu_bot_sdk import FeishuConfig

config = FeishuConfig(
    app_id="cli_xxx",
    app_secret="xxx",
    rate_limit_enabled=True,
    rate_limit_base_qps=5.0,
    rate_limit_min_qps=1.0,
    rate_limit_max_qps=50.0,
)
```

若你有自定义调用路径，也可以手动使用 `AdaptiveRateLimiter`。
