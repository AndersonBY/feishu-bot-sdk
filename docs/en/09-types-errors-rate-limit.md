# 09 Types, Errors, and Rate Limit

[中文](../zh/09-types-errors-rate-limit.md) | [Back to English Index](../README_EN.md)

## Covered Modules

- `feishu_bot_sdk.types`
- `feishu_bot_sdk.exceptions`
- `feishu_bot_sdk.rate_limit`
- `feishu_bot_sdk.response`

## Response Structures (`response`)

- Generic response: `DataResponse`
  - Meta fields: `code`, `msg`, `ok`
  - Data access: `resp.data.xxx` or direct `resp.xxx`
  - Convert to dict: `resp.to_dict()`
- Data container: `Struct`
  - Supports both attribute access (`item.record_id`) and mapping access (`item["record_id"]`)

Example:

```python
spaces = wiki.list_spaces(page_size=10)
if spaces.ok:
    print(spaces.items)
```

## Enums (`types`)

- `MemberIdType`: `open_id` / `user_id` / `union_id`
- `Permission`: `view` / `edit` / `full_access`
- `DriveResourceType`: `bitable` / `docx`

Using enums helps avoid string typos in integration code.

## Exceptions (`exceptions`)

- `SDKError`: base SDK exception
- `ConfigurationError`: invalid configuration
- `HTTPRequestError`: HTTP transport failure, with:
  - `status_code`
  - `response_text`
  - `response_headers`
- `FeishuError`: Feishu business error (`code != 0`)

Example:

```python
from feishu_bot_sdk import FeishuError, HTTPRequestError

try:
    ...
except FeishuError as exc:
    print("feishu error:", exc)
except HTTPRequestError as exc:
    print(exc.status_code, exc.response_text)
```

## Adaptive Rate Limit (`rate_limit`)

Objects:

- `RateLimitTuning`
- `AdaptiveRateLimiter`
- `AsyncAdaptiveRateLimiter`
- `build_rate_limit_key(method, path)`

`FeishuClient` enables adaptive rate limiting by default. Tune it via `FeishuConfig`:

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

You can also use `AdaptiveRateLimiter` directly for custom request workflows.
