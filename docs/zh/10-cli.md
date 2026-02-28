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
- `--tenant-access-token`：直传租户 token（可选）
- `--base-url`：默认 `https://open.feishu.cn/open-apis`
- `--timeout`：请求超时秒数

认证优先级：环境变量优先，其次命令行参数。

- 环境变量：`FEISHU_APP_ID` / `FEISHU_APP_SECRET`
- 兼容变量：`APP_ID` / `APP_SECRET`

## 常用命令

```bash
# 鉴权
feishu auth token --format json

# 发消息
feishu im send-text --receive-id ou_xxx --text "hello"
feishu im send-markdown --receive-id ou_xxx --markdown-file ./msg.md --format json

# 文件与文档
feishu media upload-file ./final.csv --format json
feishu bitable create-from-csv ./final.csv --app-name "任务结果" --table-name "结果表"
feishu docx create-from-markdown --title "日报" --markdown-file ./report.md

# Wiki
feishu wiki search-nodes --query "项目周报" --format json
```

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
