# CLI Command Reference

## Global Flags

```
--format human|json         Output format (default: human)
--app-id TEXT               Feishu app ID (env: FEISHU_APP_ID)
--app-secret TEXT           Feishu app secret (env: FEISHU_APP_SECRET)
--auth-mode tenant|user     Auth mode
--base-url URL              API base (default: https://open.feishu.cn/open-apis)
--timeout SECONDS           Request timeout
--max-output-chars INT      Stdout cap for regular command results (default: 25000)
--output-offset INT         Inspect a later slice of oversized JSON output
--save-output PATH          Write full normalized JSON to file before stdout truncation
--full-output               Disable regular-command stdout truncation
```

## Large Output Control

```bash
# Keep full JSON on disk, but return a capped stdout preview
feishu search app --query "calendar" --save-output ./search-full.json --format json

# Inspect the next JSON slice when _cli_output.next_output_offset is returned
feishu search app --query "calendar" --output-offset 25000 --max-output-chars 25000 --format json

# Disable truncation only when you explicitly want the full stdout payload
feishu search app --query "calendar" --full-output --format json
```

Agent rule:
- Prefer `--page-size` and `--page-token` for large result sets.
- Use `--all` only when the total result volume is expected to stay manageable.
- For non-paged commands such as `drive list-members`, `calendar list-freebusy`, and `calendar batch-freebusy`, prefer `--save-output`.

## auth - Authentication

```bash
# Get tenant access token
feishu auth token --format json

# Inspect current authenticated user (requires user auth)
feishu auth whoami --auth-mode user --format json

# Raw API request
feishu auth request GET /contact/v3/users/me
feishu auth request POST /im/v1/messages --params-json '{"receive_id_type":"open_id"}' \
  --payload-json '{"receive_id":"ou_xxx","msg_type":"text","content":"{\"text\":\"hi\"}"}'
```

## im - Instant Messaging

```bash
# Send text message
feishu im send-text --receive-id ou_xxx --text "Hello"

# Send markdown
feishu im send-markdown --receive-id ou_xxx --markdown "# Title\n\nContent"
feishu im send-markdown --receive-id ou_xxx --markdown-file report.md
cat report.md | feishu im send-markdown --receive-id ou_xxx --markdown-stdin

# Reply with markdown
feishu im reply-markdown om_xxx --markdown "Got it!"

# Send arbitrary message type
feishu im send --receive-id ou_xxx --msg-type text --content-json '{"text":"hello"}'
echo '{"text":"piped"}' | feishu im send --receive-id ou_xxx --msg-type text --content-stdin

# Reply to message
feishu im reply om_xxx --msg-type text --content-json '{"text":"reply"}'

# Get/recall message
feishu im get om_xxx
feishu im recall om_xxx
```

**Receive ID**: defaults to `open_id`. Override with `--receive-id-type chat_id|user_id|union_id`.

## media - Media Upload

```bash
# Upload image (returns image_key)
feishu media upload-image photo.png
feishu media upload-image avatar.jpg --image-type avatar

# Upload file (returns file_key)
feishu media upload-file document.pdf --file-type pdf
feishu media upload-file video.mp4 --file-type mp4 --duration 60000
```

## bitable - Bitable (Spreadsheet Database)

```bash
# Create bitable from CSV (returns app_token + url)
feishu bitable create-from-csv data.csv --app-name "Sales Data" --table-name "Q1"
feishu bitable create-from-csv data.csv --app-name "Sales" --table-name "Q1" --grant-member-id ou_xxx

# List tables first when you need an explicit table choice
feishu bitable list-tables --app-token bascnXXX --format json

# Create table in existing app
feishu bitable create-table --app-token bascnXXX --table-json '{"name":"Sheet2","fields":[...]}'

# CRUD records
# --table-id can be omitted when the app has a default table or exactly one table
feishu bitable create-record --app-token bascnXXX --fields-json '{"Name":"Alice","Score":95}'
feishu bitable list-records --app-token bascnXXX --table-id tblXXX --page-size 100 --format json
feishu bitable list-records --app-token bascnXXX --all --format json
feishu bitable list-views --app-token bascnXXX --format json

# Grant edit permission
feishu bitable grant-edit --app-token bascnXXX --member-id ou_xxx
feishu bitable grant-edit --app-token bascnXXX --member-id me --member-id-type open_id --auth-mode user --format json
```

## docx - Documents

```bash
# Create empty document
feishu docx create --title "Weekly Report" --format json

# Insert markdown/html content
feishu docx insert-content --document-id docXXX --content "# Section\n\nContent" --content-type markdown --format json
feishu docx insert-content --document-id docXXX --content-file content.md --content-type markdown --document-revision-id -1 --format json
cat content.md | feishu docx insert-content --document-id docXXX --content-stdin --content-type markdown --format json

# insert-content returns a compact summary by default; add --full-response only for debugging
feishu docx insert-content --document-id docXXX --content-file content.md --content-type markdown --full-response --format json

# Grant edit permission
feishu docx grant-edit --document-id docXXX --member-id ou_xxx --format json
feishu docx grant-edit --document-id docXXX --member-id me --member-id-type open_id --auth-mode user --format json

# Export document as markdown
feishu docx get-content --doc-token docXXX --doc-type docx --content-type markdown --format json
feishu docx get-content --doc-token docXXX --doc-type wiki_doc --content-type markdown --output ./doc.md --format json
```

## drive - Drive Files

```bash
# Upload file to drive
feishu drive upload-file report.pdf --parent-type explorer --parent-node fldcnXXX

# Import/export tasks
feishu drive create-import-task --task-json '{"file_extension":"csv","file_token":"xxx","type":"bitable",...}'
feishu drive get-import-task TICKET_ID

feishu drive create-export-task --task-json '{"token":"xxx","type":"bitable"}'
feishu drive get-export-task TICKET_ID --token xxx

# Permissions
feishu drive grant-edit --token docXXX --resource-type docx --member-id ou_xxx --permission edit --format json
feishu drive grant-edit --token docXXX --resource-type docx --member-id me --member-id-type open_id --permission edit --auth-mode user --format json
feishu drive list-members --token docXXX --resource-type docx --format json
feishu drive list-members --token docXXX --resource-type docx --save-output ./drive-members.json --format json
```

## wiki - Knowledge Base

```bash
# List wiki spaces
feishu wiki list-spaces --page-size 20 --format json
feishu wiki list-spaces --all --format json

# Search nodes
feishu wiki search-nodes --query "project plan" --space-id spaceXXX --page-size 20 --format json
feishu wiki search-nodes --query "project plan" --space-id spaceXXX --all --format json

# Get node details
feishu wiki get-node --token wikiXXX --format json

# List child nodes
feishu wiki list-nodes --space-id spaceXXX --parent-node-token wikiXXX --page-size 20 --format json
```

## calendar - Calendars and Events

```bash
# Calendars
feishu calendar list-calendars --page-size 50 --format json
feishu calendar list-calendars --all --format json
feishu calendar search-calendars --query "eng" --page-size 20 --format json
feishu calendar search-calendars --query "eng" --all --format json

# Events
feishu calendar list-events --calendar-id calXXX --page-size 100 --format json
feishu calendar list-events --calendar-id calXXX --all --format json
feishu calendar search-events --calendar-id calXXX --query "weekly" --page-size 50 --format json
feishu calendar search-events --calendar-id calXXX --all --format json

# Freebusy results can be large and are not paged by the CLI; save before inspection
feishu calendar list-freebusy --request-file freebusy.json --save-output ./freebusy.json --format json
feishu calendar batch-freebusy --request-file batch-freebusy.json --save-output ./batch-freebusy.json --format json
```

## contact - Users and Departments

```bash
# Users
feishu contact user get --user-id ou_xxx --user-id-type open_id --format json
feishu contact user by-department --department-id od_xxx --page-size 50 --format json
feishu contact user by-department --department-id od_xxx --all --format json
feishu contact user search --query "Alice" --page-size 20 --auth-mode user --format json
feishu contact user search --query "Alice" --all --auth-mode user --format json

# Departments and scopes
feishu contact department children --department-id od_xxx --page-size 50 --format json
feishu contact department children --department-id od_xxx --all --format json
feishu contact department parent --department-id od_xxx --all --format json
feishu contact department search --query "engineering" --all --format json
feishu contact scope get --page-size 100 --format json
feishu contact scope get --all --format json
```

## webhook - Webhook Processing

```bash
# Decode encrypted webhook body
feishu webhook decode --body-json '{"encrypt":"..."}' --encrypt-key KEY

# Verify signature
feishu webhook verify-signature --headers-json '{"X-Lark-Signature":"...","X-Lark-Request-Timestamp":"...","X-Lark-Request-Nonce":"..."}' \
  --body-json '{"..."}' --encrypt-key KEY

# Handle challenge
feishu webhook challenge --challenge "feishu_xxx"

# Parse webhook event
feishu webhook parse --body-json '{"..."}' --encrypt-key KEY

# Start webhook HTTP server
feishu webhook serve --host 0.0.0.0 --port 8000 --path /webhook/feishu --print-payload
feishu webhook serve --max-requests 5  # Stop after 5 requests
```

## ws - WebSocket

```bash
# Get WebSocket endpoint info
feishu ws endpoint --format json

# Listen for events via WebSocket
feishu ws run --print-payload
feishu ws run --event-type im.message.receive_v1 --max-events 10
feishu ws run --duration-seconds 300
```

## server - Managed Bot Server

```bash
# Run bot server (foreground, blocks until SIGINT)
feishu server run --print-payload
feishu server run --event-type im.message.receive_v1

# Daemon mode
feishu server start --pid-file /tmp/feishu.pid --log-file /tmp/feishu.log
feishu server status --pid-file /tmp/feishu.pid --format json
feishu server stop --pid-file /tmp/feishu.pid
```

## Stdin Piping Patterns

All commands with `--*-json` also support `--*-file PATH` and `--*-stdin`:

```bash
# Pipe markdown from another command
generate_report | feishu im send-markdown --receive-id ou_xxx --markdown-stdin --format json

# Pipe JSON payload
echo '{"text":"hello"}' | feishu im send --receive-id ou_xxx --msg-type text --content-stdin

# Pipe from file
feishu im send --receive-id ou_xxx --msg-type interactive --content-file card.json
```
