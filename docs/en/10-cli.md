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
- `--auth-mode tenant|user`: auth mode, default is `tenant`
- `--access-token`: optional static access token for current auth mode
- `--app-access-token`: optional app token for OAuth code/refresh exchange
- `--user-access-token` / `--user-refresh-token`: user tokens (common with `auth_mode=user`)
- `--profile`: local token profile (default from `FEISHU_PROFILE` or `default`)
- `--token-store`: local token store path
- `--no-store`: disable local token store read/write
- `--base-url`: default `https://open.feishu.cn/open-apis`
- `--timeout`: request timeout seconds

Auth precedence: environment variables > CLI flags > local token store.

- Env vars: `FEISHU_APP_ID` / `FEISHU_APP_SECRET` / `FEISHU_AUTH_MODE` / `FEISHU_ACCESS_TOKEN`
- User auth env vars: `FEISHU_USER_ACCESS_TOKEN` / `FEISHU_USER_REFRESH_TOKEN`
- OAuth exchange env var: `FEISHU_APP_ACCESS_TOKEN`
- Token store env vars: `FEISHU_PROFILE` / `FEISHU_TOKEN_STORE_PATH` / `FEISHU_NO_STORE`
- Compatible vars: `APP_ID` / `APP_SECRET`

## Common Commands

```bash
# auth (recommended: localhost callback, no public URL)
feishu auth token --format json
feishu auth login --scope "offline_access contact:user.base:readonly" --no-browser --format json
feishu auth whoami --format json
feishu auth refresh --format json
feishu auth logout --format json

# low-level OAuth debug commands
feishu oauth authorize-url --redirect-uri https://example.com/callback --format json
feishu oauth exchange-code --code CODE --format json

# messaging
feishu im send-text --receive-id ou_xxx --text "hello"
feishu im send-markdown --receive-id ou_xxx --markdown-file ./msg.md --format json
feishu im push-follow-up om_xxx --follow-ups-json '[{"content":"continue"}]' --format json
feishu im forward-thread omt_xxx --receive-id-type chat_id --receive-id oc_xxx --format json
feishu im update-url-previews --preview-token token_1 --preview-token token_2 --open-id ou_xxx --format json

# file and docs
feishu media upload-file ./final.csv --format json
feishu media download-file file_xxx ./downloads/file.bin --format json
feishu bitable create-from-csv ./final.csv --app-name "Task Result" --table-name "Result"
feishu bitable list-records --app-token app_xxx --table-id tbl_xxx --all --format json
feishu docx create-from-markdown --title "Daily Report" --markdown-file ./report.md
feishu docx get-markdown --doc-token doccn_xxx --doc-type docx --format json
feishu drive grant-edit --token doccn_xxx --resource-type docx --member-id ou_xxx --permission edit --format json

# wiki
feishu wiki search-nodes --query "weekly report" --all --format json
feishu wiki list-spaces --all --format json

# search
feishu search app --query "approval" --auth-mode user --format json
feishu search message --query "incident" --chat-type group_chat --auth-mode user --format json
feishu search doc-wiki --query "weekly report" --doc-filter-json '{"only_title": true}' --auth-mode user --format json

# contact
feishu contact user get --user-id ou_xxx --user-id-type open_id --format json
feishu contact user by-department --department-id od_xxx --page-size 20 --format json
feishu contact department search --query "engineering" --format json
feishu contact scope get --page-size 100 --format json

# calendar
feishu calendar list-calendars --page-size 50 --format json
feishu calendar create-event --calendar-id cal_xxx --event-file ./event.json --format json
feishu calendar attach-material --calendar-id cal_xxx --event-id evt_xxx --path ./agenda.md --format json
```

## User Auth (CLI Best Practice)

`feishu auth login` uses a local callback by default (`http://127.0.0.1:18080/callback`) and enables PKCE.

- Step 1: add the localhost redirect URL in Feishu app security settings
- Step 2: run `feishu auth login`
- Step 3: use `feishu auth whoami` and other `auth_mode=user` commands directly

Automatic behavior:

- pre-refresh near-expiry access tokens (default 300 seconds before expiry)
- on token-invalid API responses, auto-refresh and retry once
- persist refreshed token pairs to local token store (including rotated refresh token)

## Content Commands (Agent Tips)

- Prefer `--all` for paged queries: `bitable list-records`, `wiki list-spaces`, `wiki search-nodes`, `wiki list-nodes`
- `bitable list-records` now supports `--view-id`, `--filter`, `--sort`, `--field-names`, and `--text-field-as-array`
- Permission-related flags now use strict choices: `--member-id-type`, `--resource-type`, `--permission`
- `docx get-markdown --doc-type` is now restricted to official supported values

## Calendar Attachments (Strongly Recommended for Agents)

To avoid `193107 no permission to access attachment file token`, do not upload with a wrong media upload point and then patch the event.

Use:

```bash
feishu calendar attach-material --calendar-id cal_xxx --event-id evt_xxx --path ./agenda.md --format json
```

This command automatically:

- uploads with `parent_type=calendar`
- uploads with `parent_node=<calendar_id>`
- updates event `attachments` (default append mode; use `--mode replace` to overwrite)

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
