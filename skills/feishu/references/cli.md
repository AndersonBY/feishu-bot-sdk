# CLI Command Reference

## Global Flags

```
--format human|json     Output format (default: human)
--app-id TEXT           Feishu app ID (env: FEISHU_APP_ID)
--app-secret TEXT       Feishu app secret (env: FEISHU_APP_SECRET)
--tenant-access-token   Direct token (skip auth)
--base-url URL          API base (default: https://open.feishu.cn/open-apis)
--timeout SECONDS       Request timeout
```

## auth - Authentication

```bash
# Get tenant access token
feishu auth token --format json

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

# Create table in existing app
feishu bitable create-table --app-token bascnXXX --table-json '{"name":"Sheet2","fields":[...]}'

# CRUD records
feishu bitable create-record --app-token bascnXXX --table-id tblXXX --fields-json '{"Name":"Alice","Score":95}'
feishu bitable list-records --app-token bascnXXX --table-id tblXXX --page-size 100

# Grant edit permission
feishu bitable grant-edit --app-token bascnXXX --member-id ou_xxx
```

## docx - Documents

```bash
# Create empty document
feishu docx create --title "Weekly Report"

# Append markdown content
feishu docx append-markdown --document-id docXXX --markdown "# Section\n\nContent"
feishu docx append-markdown --document-id docXXX --markdown-file content.md
cat content.md | feishu docx append-markdown --document-id docXXX --markdown-stdin

# Create document with markdown content in one step
feishu docx create-from-markdown --title "Report" --markdown-file report.md

# Grant edit permission
feishu docx grant-edit --document-id docXXX --member-id ou_xxx

# Export document as markdown
feishu docx get-markdown --doc-token docXXX
feishu docx get-markdown --doc-token docXXX --doc-type wiki_doc
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
feishu drive grant-edit --token docXXX --resource-type docx --member-id ou_xxx
feishu drive list-members --token docXXX --resource-type docx
```

## wiki - Knowledge Base

```bash
# List wiki spaces
feishu wiki list-spaces --page-size 20

# Search nodes
feishu wiki search-nodes --query "project plan" --space-id spaceXXX

# Get node details
feishu wiki get-node --token wikiXXX

# List child nodes
feishu wiki list-nodes --space-id spaceXXX --parent-node-token wikiXXX
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
