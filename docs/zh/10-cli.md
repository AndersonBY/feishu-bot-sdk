# CLI 命令行工具

[English](../en/10-cli.md)

`feishu-bot-sdk` 提供 `feishu` 命令，适合脚本、CI 和 LLM Agent 直接调用。

## CLI 架构

CLI 基于 Click 框架，采用三层命令模型：

- 顶层命令：`api`、`schema`、`doctor`、`completion`、`webhook`、`ws`、`server`、`media`
- 高价值工作流命令：`+shortcut`（如 `bitable +create-from-csv`、`docx +insert-content`）
- service command：metadata 驱动的 API 调用，`feishu <service> <resource> <method> --params ... --data ...`

优先级建议：

1. 有 `+shortcut` 先用 `+shortcut`
2. 需要底层能力时先看 `feishu schema ...`
3. 再执行 generated service command
4. 最后使用 `feishu api` 直接调用

补充说明见：

- [CLI 框架决策](../cli-framework-decision.md)
- [CLI 命令映射](../cli-command-mapping.md)

## 安装

```bash
uv tool install feishu-bot-sdk
feishu --help
```

## 公开运行时参数

所有 Click 命令的统一参数：

- `--format json|pretty|table|csv|ndjson`
- `--as user|bot|auto`
- `--profile`
- `--app-id` / `--app-secret`
- `--max-output-chars` / `--output-offset` / `--save-output` / `--full-output`
- service/raw API 额外支持：`--params` / `--data` / `--page-all` / `--page-size` / `--page-limit` / `--page-delay` / `--output` / `--dry-run`

认证优先级：环境变量 > 命令行参数 > CLI profile > 本地 token store profile。

- 环境变量：`FEISHU_APP_ID` / `FEISHU_APP_SECRET` / `FEISHU_AUTH_MODE` / `FEISHU_ACCESS_TOKEN`
- 用户态环境变量：`FEISHU_USER_ACCESS_TOKEN` / `FEISHU_USER_REFRESH_TOKEN`
- OAuth 交换环境变量：`FEISHU_APP_ACCESS_TOKEN`
- CLI 配置 / Store 变量：`FEISHU_PROFILE` / `FEISHU_CLI_CONFIG_PATH` / `FEISHU_SECRET_STORE_PATH` / `FEISHU_SECRET_STORE_KEY_PATH` / `FEISHU_TOKEN_STORE_PATH` / `FEISHU_NO_STORE`
- 兼容变量：`APP_ID` / `APP_SECRET`

## Profile 初始化

推荐先配置一个 CLI profile，再执行后续 `auth` / domain 命令：

```bash
printf 'app_secret' | feishu config init --profile default --app-id cli_xxx --app-secret-stdin --default-as auto --set-default --format json
feishu config show --format json
feishu config list-profiles --format json
feishu config migrate-token-store --source-path ~/.config/feishu-bot-sdk/tokens.json --app-id cli_xxx --format json
```

如果你已经有旧版 `tokens.json`，可用 `config migrate-token-store` 把旧 profile 名称与 token store 路径导入到新版 CLI config；旧 token 文件本身不会被删除。

## 大输出控制

- 常规命令默认把 stdout 控制在 `25000` 字符内，避免脚本和 LLM Agent 被超长 JSON 挤爆上下文。
- 如果返回被截断，CLI 会在 `_cli_output` 里给出：
  - `next_output_offset`：下一段 JSON 片段的起始偏移
  - `paging.next_page_token`：如果接口本身支持翻页，会给出下一页 token
  - `hints`：下一步可直接执行的命令建议
- 查看后续片段：`feishu ... --output-offset 25000 --max-output-chars 25000 --format json`
- 保留完整结果：`feishu ... --save-output ./full.json --format json`
- 如果命令本身支持翻页，优先用 `--page-size` / `--page-token`，谨慎使用 `--all`

## JSON 错误 Envelope

当使用 `--format json` 时，失败结果统一返回结构化 envelope：

```json
{
  "ok": false,
  "error": {
    "type": "http_error",
    "code": 99991679,
    "message": "http request failed",
    "hint": "missing user scopes; re-authorize with ...",
    "retryable": false
  },
  "exit_code": 4
}
```

`error` 对象还可能额外带上 `status_code`、`response_excerpt` 等传输层诊断字段。

## 常用命令

```bash
# 配置 / profile
feishu config init --profile default --app-id cli_xxx --app-secret-file ./.secrets/feishu_app_secret --set-default --format json
feishu config show --profile default --format json
feishu config set-default-profile default --format json
feishu config migrate-token-store --source-path ./tokens.json --default-profile default --format json
feishu config remove-profile default --format json

# 鉴权
feishu auth token --format json
feishu auth login --scope "offline_access contact:user.base:readonly" --no-browser --format json
feishu auth whoami --format json
feishu auth refresh --format json
feishu auth logout --format json
feishu auth status --format json
feishu auth check --scope "contact:user:search" --format json

# 通用 API 调用
feishu api GET /open-apis/contact/v3/users/ou_xxx --format json
feishu api POST /open-apis/im/v1/messages --data '{"receive_id":"ou_xxx","content":"{\"text\":\"hello\"}","msg_type":"text"}' --params '{"receive_id_type":"open_id"}' --format json

# 文件与文档
feishu media upload-file ./final.csv --format json
feishu media download-file file_xxx ./downloads/file.bin --format json
feishu media download-file img_v3_xxx ./downloads/image.jpg --format json
feishu media download-file img_v3_xxx ./downloads/image.jpg --message-id om_xxx --resource-type image --format json
feishu bitable +create-from-csv ./final.csv --app-name "任务结果" --table-name "结果表"
feishu docx +insert-content --document-id doccn_xxx --content-file ./report.md --content-type markdown --document-revision-id -1 --format json
# `--content-file` 模式下，相对本地图片路径按 Markdown 文件所在目录解析
feishu drive +requester-upload ./final.csv --folder-name "Uploads" --format json

# 日历附件
feishu calendar +attach-material ./agenda.md --calendar-id cal_xxx --event-id evt_xxx --format json

# 任务
feishu task +create --summary "跟进合同" --assignee ou_xxx --due +2d --format json
feishu task +comment --task-id task_xxx --content "已联系客户" --format json
feishu task +delete --task-id task_xxx --format json
feishu task +assign --task-id task_xxx --add ou_xxx,ou_yyy --format json
feishu task +reminder --task-id task_xxx --set 1h --format json
feishu task +get-my-tasks --as user --query "合同" --page-all --format json

# 邮件
feishu mail +send-markdown --user-mailbox-id me --to-email user@example.com --subject "日报" --markdown-file ./report.md --format json
```

## User Auth（CLI 最佳实践）

`feishu auth login` 默认优先走 device flow；当你显式传入 `--localhost`，或使用 `--redirect-uri` / `--state` / `--no-browser` / `--no-pkce` 这类本地回调参数时，会切回 localhost callback。

- 第一步：无浏览器/Agent 场景优先直接执行 `feishu auth login --device-code`
- 第二步：如果你要本地浏览器回调，再去飞书开发者后台安全设置中添加 localhost 重定向 URL，并执行 `feishu auth login --localhost`
- 第三步：后续直接执行 `feishu auth whoami` 或其它需要 user identity 的命令

自动处理策略：

- access token 临近过期（默认提前 300 秒）会自动 refresh
- 接口返回 token 失效相关错误时会自动 refresh 并重试 1 次
- refresh 成功后会自动更新本地 token store（包含新 refresh token）

## 日历附件（Agent 强烈建议）

为避免 `193107 no permission to access attachment file token`，不要手动先传错误上传点再更新日程。

直接使用：

```bash
feishu calendar +attach-material ./agenda.md --calendar-id cal_xxx --event-id evt_xxx --format json
```

该命令会自动：

- 上传素材时使用 `parent_type=calendar`
- 上传素材时使用 `parent_node=<calendar_id>`
- 更新日程 `attachments`（默认追加模式，可通过 `--mode replace` 覆盖）

## 事件与长连接

```bash
# Webhook 工具
feishu webhook parse --body-file ./webhook.json --format json
feishu webhook verify-signature --headers-file ./headers.json --body-file ./raw_body.json --encrypt-key xxx
feishu webhook serve --host 127.0.0.1 --port 8000 --path /webhook/feishu --max-requests 10

# 获取 WS endpoint
feishu ws endpoint --format json

# 低层 WS 监听（可自动退出）
feishu ws run --max-events 1 --output-file ./events.jsonl --format json

# 一站式服务模式（FeishuBotServer）
feishu server run --print-payload --output-file ./events.jsonl

# 后台托管服务
feishu server start --pid-file ./.feishu_server.pid --log-file ./feishu-server.log
feishu server status --pid-file ./.feishu_server.pid --format json
feishu server stop --pid-file ./.feishu_server.pid
```

`ws run` / `server run` 支持：

- `--event-type`：可重复，按事件类型过滤
- `--print-payload`：输出完整 payload
- `--output-file`：JSON Lines 落盘
- `--max-events`：收到 N 个事件后自动停止

`webhook serve` 支持：

- `--encrypt-key` / `--verification-token`
- `--no-verify-signatures`
- `--event-type`、`--print-payload`、`--output-file`
- `--max-requests`：处理 N 个请求后自动退出
