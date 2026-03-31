# CLI Tool

[中文版](../zh/10-cli.md)

`feishu-bot-sdk` ships a `feishu` command for scripts, CI, and LLM Agent workflows.

## CLI Architecture

The CLI is built on Click with a three-layer command model:

- top-level commands: `api`, `schema`, `doctor`, `completion`, `webhook`, `ws`, `server`, `media`
- high-value workflow commands: `+shortcut` (e.g., `bitable +create-from-csv`, `docx +insert-content`)
- service commands: metadata-driven API calls, `feishu <service> <resource> <method> --params ... --data ...`

Recommended order:

1. use `+shortcut` when it exists
2. inspect `feishu schema ...`
3. call the generated service command
4. use `feishu api` for direct API calls

See also:

- [CLI Framework Decision](../cli-framework-decision.md)
- [CLI Command Mapping](../cli-command-mapping.md)

## Install

```bash
uv tool install feishu-bot-sdk
feishu --help
```

## Public Runtime Flags

All Click commands expose these runtime flags:

- `--format json|pretty|table|csv|ndjson`
- `--as user|bot|auto`
- `--profile`
- `--app-id` / `--app-secret`
- `--max-output-chars` / `--output-offset` / `--save-output` / `--full-output`
- service/raw API commands also support `--params` / `--data` / `--page-all` / `--page-size` / `--page-limit` / `--page-delay` / `--output` / `--dry-run`

Auth precedence: environment variables > CLI flags > CLI profile > local token store profile.

- Env vars: `FEISHU_APP_ID` / `FEISHU_APP_SECRET` / `FEISHU_AUTH_MODE` / `FEISHU_ACCESS_TOKEN`
- User auth env vars: `FEISHU_USER_ACCESS_TOKEN` / `FEISHU_USER_REFRESH_TOKEN`
- OAuth exchange env var: `FEISHU_APP_ACCESS_TOKEN`
- CLI config / store env vars: `FEISHU_PROFILE` / `FEISHU_CLI_CONFIG_PATH` / `FEISHU_SECRET_STORE_PATH` / `FEISHU_SECRET_STORE_KEY_PATH` / `FEISHU_TOKEN_STORE_PATH` / `FEISHU_NO_STORE`
- Compatible vars: `APP_ID` / `APP_SECRET`

## Profile Bootstrap

Recommended first step: configure a CLI profile, then use the rest of the `auth` and domain commands against that profile.

```bash
printf 'app_secret' | feishu config init --profile default --app-id cli_xxx --app-secret-stdin --default-as auto --set-default --format json
feishu config show --format json
feishu config list-profiles --format json
feishu config migrate-token-store --source-path ~/.config/feishu-bot-sdk/tokens.json --app-id cli_xxx --format json
```

If you already have an old `tokens.json`, use `config migrate-token-store` to import the old profile names and token store path into the CLI config. The old token file itself is left in place.

## Large Output Control

- Regular command stdout is capped at `25000` characters by default so scripts and LLM Agents do not get flooded by oversized JSON payloads.
- When output is truncated, `_cli_output` includes:
  - `next_output_offset`: the next JSON slice offset
  - `paging.next_page_token`: the next page token when the API itself is paged
  - `hints`: concrete follow-up commands
- Inspect the next slice: `feishu ... --output-offset 25000 --max-output-chars 25000 --format json`
- Keep the full result on disk: `feishu ... --save-output ./full.json --format json`
- Prefer `--page-size` / `--page-token` over `--all` when the command supports paging

## JSON Error Envelope

When `--format json` is used, command failures return a structured envelope:

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

The `error` object may also include transport-specific fields such as `status_code` and `response_excerpt`.

## Common Commands

```bash
# config / profile
feishu config init --profile default --app-id cli_xxx --app-secret-file ./.secrets/feishu_app_secret --set-default --format json
feishu config show --profile default --format json
feishu config set-default-profile default --format json
feishu config migrate-token-store --source-path ./tokens.json --default-profile default --format json
feishu config remove-profile default --format json

# auth
feishu auth token --format json
feishu auth login --scope "offline_access contact:user.base:readonly" --no-browser --format json
feishu auth whoami --format json
feishu auth refresh --format json
feishu auth logout --format json
feishu auth status --format json
feishu auth check --scope "contact:user:search" --format json

# generic API call
feishu api GET /open-apis/contact/v3/users/ou_xxx --format json
feishu api POST /open-apis/im/v1/messages --data '{"receive_id":"ou_xxx","content":"{\"text\":\"hello\"}","msg_type":"text"}' --params '{"receive_id_type":"open_id"}' --format json

# files and docs
feishu media upload-file ./final.csv --format json
feishu media download-file file_xxx ./downloads/file.bin --format json
feishu media download-file img_v3_xxx ./downloads/image.jpg --message-id om_xxx --resource-type image --format json
feishu bitable +create-from-csv ./final.csv --app-name "Task Result" --table-name "Result"
feishu docx +insert-content --document-id doccn_xxx --content-file ./report.md --content-type markdown --document-revision-id -1 --format json
# In `--content-file` mode, relative local image paths resolve against the Markdown file directory
feishu drive +requester-upload ./final.csv --folder-name "Uploads" --format json

# calendar attachments
feishu calendar +attach-material ./agenda.md --calendar-id cal_xxx --event-id evt_xxx --format json

# mail
feishu mail +send-markdown --user-mailbox-id me --to-email user@example.com --subject "Daily Report" --markdown-file ./report.md --format json
```

## User Auth (CLI Best Practice)

`feishu auth login` prefers device flow by default. It switches to localhost callback when you explicitly pass `--localhost`, or when you use localhost-oriented flags such as `--redirect-uri`, `--state`, `--no-browser`, or `--no-pkce`.

- Step 1: for browserless or agent flows, run `feishu auth login --device-code`
- Step 2: for browser callback flows, add the localhost redirect URL in Feishu app security settings and run `feishu auth login --localhost`
- Step 3: use `feishu auth whoami` and other commands that require user identity directly

Automatic behavior:

- pre-refresh near-expiry access tokens (default 300 seconds before expiry)
- on token-invalid API responses, auto-refresh and retry once
- persist refreshed token pairs to local token store (including rotated refresh token)

## Calendar Attachments (Strongly Recommended for Agents)

To avoid `193107 no permission to access attachment file token`, do not upload with a wrong media upload point and then patch the event.

Use:

```bash
feishu calendar +attach-material ./agenda.md --calendar-id cal_xxx --event-id evt_xxx --format json
```

This command automatically:

- uploads with `parent_type=calendar`
- uploads with `parent_node=<calendar_id>`
- updates event `attachments` (default append mode; use `--mode replace` to overwrite)

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
