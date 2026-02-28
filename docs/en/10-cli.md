# CLI Tool

[中文版](../zh/10-cli.md)

`feishu-bot-sdk` ships a `feishu` command for scripts, CI, and LLM Agent workflows.

## Install

```bash
uv tool install feishu-bot-sdk
feishu --help
```

## Global Flags

- `--format human|json`: default is `human`; use `json` for machine workflows
- `--app-id` / `--app-secret`: app credentials
- `--tenant-access-token`: optional direct tenant token
- `--base-url`: default `https://open.feishu.cn/open-apis`
- `--timeout`: request timeout seconds

Auth precedence: environment variables first, then CLI flags.

- Env vars: `FEISHU_APP_ID` / `FEISHU_APP_SECRET`
- Compatible vars: `APP_ID` / `APP_SECRET`

## Common Commands

```bash
# auth
feishu auth token --format json

# messaging
feishu im send-text --receive-id ou_xxx --text "hello"
feishu im send-markdown --receive-id ou_xxx --markdown-file ./msg.md --format json

# file and docs
feishu media upload-file ./final.csv --format json
feishu bitable create-from-csv ./final.csv --app-name "Task Result" --table-name "Result"
feishu docx create-from-markdown --title "Daily Report" --markdown-file ./report.md

# wiki
feishu wiki search-nodes --query "weekly report" --format json
```

## Stdin (Agent-friendly)

Many commands can read input from stdin for pipeline workflows:

```bash
# Markdown from stdin
cat report.md | feishu im send-markdown --receive-id ou_xxx --markdown-stdin --format json

# JSON from stdin
echo '{"text":"hello"}' | feishu im send --receive-id ou_xxx --msg-type text --content-stdin --format json
echo '{"x":1}' | feishu auth request POST /some/path --payload-stdin --format json
```

## Events and Long Connection

```bash
# webhook helpers
feishu webhook parse --body-file ./webhook.json --format json
feishu webhook verify-signature --headers-file ./headers.json --body-file ./raw_body.json --encrypt-key xxx
feishu webhook serve --host 127.0.0.1 --port 8000 --path /webhook/feishu --max-requests 10

# fetch WS endpoint
feishu ws endpoint --format json

# low-level WS listener (auto stop)
feishu ws run --max-events 1 --output-file ./events.jsonl --format json

# turnkey service mode (FeishuBotServer)
feishu server run --print-payload --output-file ./events.jsonl

# background managed service
feishu server start --pid-file ./.feishu_server.pid --log-file ./feishu-server.log
feishu server status --pid-file ./.feishu_server.pid --format json
feishu server stop --pid-file ./.feishu_server.pid
```

`ws run` and `server run` support:

- `--event-type`: repeatable event type filters
- `--print-payload`: include full payload
- `--output-file`: append JSON lines
- `--max-events`: auto-stop after N events

`webhook serve` supports:

- `--encrypt-key` / `--verification-token`
- `--no-verify-signatures`
- `--event-type`, `--print-payload`, `--output-file`
- `--max-requests`: auto-stop after handling N requests
