# CLI 命令行工具

[English](../en/10-cli.md)

`feishu-bot-sdk` 提供 `feishu` 命令，适合脚本、CI 和 LLM Agent 直接调用。

## 安装

```bash
uv tool install feishu-bot-sdk
feishu --help
```

## 全局参数

- `--format human|json`：默认 `human`，机器调用建议 `json`
- `--app-id` / `--app-secret`：飞书应用凭证
- `--auth-mode tenant|user`：认证模式，默认 `tenant`
- `--access-token`：当前认证模式的静态 access token（可选）
- `--app-access-token`：OAuth code/refresh 交换使用（可选）
- `--user-access-token` / `--user-refresh-token`：用户态 token（`auth_mode=user` 常用）
- `--base-url`：默认 `https://open.feishu.cn/open-apis`
- `--timeout`：请求超时秒数

认证优先级：环境变量优先，其次命令行参数。

- 环境变量：`FEISHU_APP_ID` / `FEISHU_APP_SECRET` / `FEISHU_AUTH_MODE` / `FEISHU_ACCESS_TOKEN`
- 用户态环境变量：`FEISHU_USER_ACCESS_TOKEN` / `FEISHU_USER_REFRESH_TOKEN`
- OAuth 交换环境变量：`FEISHU_APP_ACCESS_TOKEN`
- 兼容变量：`APP_ID` / `APP_SECRET`

## 常用命令

```bash
# 鉴权
feishu auth token --format json
feishu oauth authorize-url --redirect-uri https://example.com/callback --format json
feishu oauth exchange-code --code CODE --format json
feishu oauth user-info --auth-mode user --user-access-token u-xxx --format json

# 发消息
feishu im send-text --receive-id ou_xxx --text "hello"
feishu im send-markdown --receive-id ou_xxx --markdown-file ./msg.md --format json

# 文件与文档
feishu media upload-file ./final.csv --format json
feishu media download-file file_xxx ./downloads/file.bin --format json
feishu bitable create-from-csv ./final.csv --app-name "任务结果" --table-name "结果表"
feishu docx create-from-markdown --title "日报" --markdown-file ./report.md

# Wiki
feishu wiki search-nodes --query "项目周报" --format json

# 日历
feishu calendar list-calendars --page-size 50 --format json
feishu calendar create-event --calendar-id cal_xxx --event-file ./event.json --format json
feishu calendar attach-material --calendar-id cal_xxx --event-id evt_xxx --path ./agenda.md --format json
```

## 日历附件（Agent 强烈建议）

为避免 `193107 no permission to access attachment file token`，不要手动先传错误上传点再更新日程。

直接使用：

```bash
feishu calendar attach-material --calendar-id cal_xxx --event-id evt_xxx --path ./agenda.md --format json
```

该命令会自动：

- 上传素材时使用 `parent_type=calendar`
- 上传素材时使用 `parent_node=<calendar_id>`
- 更新日程 `attachments`（默认追加模式，可通过 `--mode replace` 覆盖）

## Stdin（Agent 推荐）

很多命令支持直接从标准输入读取，适合 LLM/脚本管道：

```bash
# Markdown from stdin
cat report.md | feishu im send-markdown --receive-id ou_xxx --markdown-stdin --format json

# JSON from stdin
echo '{"text":"hello"}' | feishu im send --receive-id ou_xxx --msg-type text --content-stdin --format json
echo '{"x":1}' | feishu auth request POST /some/path --payload-stdin --format json
```

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
