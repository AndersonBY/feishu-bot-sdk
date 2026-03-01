# feishu-bot-sdk

A lightweight Python SDK for Feishu bot integrations, including:

- Tenant access token retrieval and caching
- IM messaging (send/reply/edit/recall/forward/merge-forward/reaction/pin/batch/urgent/cards)
- Image/file/message-resource upload and download
- Drive file/media upload & download with import/export tasks
- Drive permissions (members, public settings, password, owner transfer)
- Bitable features (CSV import + table/field/record CRUD + batch + pagination iterators)
- Wiki APIs (space/node/member/search/task) and Docs content export (`docs/v1/content`)
- Markdown append to Docx
- Webhook callbacks and long connections (WebSocket)
- Typed event models (IM/card/URL preview/Bitable record & field changed)
- Adaptive rate limiter (auto backoff/recovery by endpoint feedback)
- Both sync and async APIs

## Install

```bash
# pip
pip install feishu-bot-sdk

# uv
uv add feishu-bot-sdk

# Install as a global CLI tool (recommended for Agent workflows)
uv tool install feishu-bot-sdk
feishu --help
```

## CLI Usage (`feishu`)

- Command name: `feishu`
- Default output: human-friendly
- Machine-readable output: add `--format json`
- Auth priority: environment variables first, then global flags
  - Env: `FEISHU_APP_ID`, `FEISHU_APP_SECRET` (also supports `APP_ID`, `APP_SECRET`)
  - Flags: `--app-id`, `--app-secret`

Examples:

```bash
# 1) Get tenant token (JSON output)
feishu auth token --format json

# 2) Send text message (human output by default)
feishu im send-text --receive-id ou_xxx --text "hello from cli"

# 3) Send markdown from file
feishu im send-markdown --receive-id ou_xxx --markdown-file ./msg.md

# 4) Reply markdown (JSON output)
feishu im reply-markdown om_xxx --markdown "### received" --format json

# 5) Upload image
feishu media upload-image ./demo.png

# 6) Create Bitable from CSV and grant access
feishu bitable create-from-csv ./final.csv --app-name "Task Result" --table-name "Result" --grant-member-id ou_xxx

# 7) Create and append markdown to Docx
feishu docx create-from-markdown --title "Daily Report" --markdown-file ./report.md

# 8) Upload file to Drive
feishu drive upload-file ./final.csv --parent-type explorer --parent-node fld_xxx

# 9) Search wiki nodes
feishu wiki search-nodes --query "weekly report" --format json

# 10) Parse webhook envelope
feishu webhook parse --body-file ./webhook.json --format json

# 11) Fetch long-connection endpoint
feishu ws endpoint --format json

# 12) Run long-connection server and print events
feishu server run --print-payload

# 13) Run local webhook server (auto-stop after 10 requests)
feishu webhook serve --host 127.0.0.1 --port 8000 --path /webhook/feishu --max-requests 10

# 14) Start / check / stop long-connection service in background
feishu server start --pid-file ./.feishu_server.pid --log-file ./feishu-server.log
feishu server status --pid-file ./.feishu_server.pid --format json
feishu server stop --pid-file ./.feishu_server.pid

# 15) Agent pipeline input (stdin)
cat ./msg.md | feishu im send-markdown --receive-id ou_xxx --markdown-stdin --format json
```

## Module Docs

- Docs index (Chinese): [`docs/README.md`](./docs/README.md)
- Docs index (English): [`docs/README_EN.md`](./docs/README_EN.md)
- Core client and config: [`docs/en/01-core-client.md`](./docs/en/01-core-client.md)
- IM messaging and media: [`docs/en/02-im.md`](./docs/en/02-im.md)
- Drive files and permissions: [`docs/en/03-drive.md`](./docs/en/03-drive.md)
- Bitable: [`docs/en/04-bitable.md`](./docs/en/04-bitable.md)
- Docx and Docs content: [`docs/en/05-docx-and-docs.md`](./docs/en/05-docx-and-docs.md)
- Wiki: [`docs/en/06-wiki.md`](./docs/en/06-wiki.md)
- Event system (Events/Webhook/WS): [`docs/en/07-events-webhook-ws.md`](./docs/en/07-events-webhook-ws.md)
- FeishuBotServer long-connection service: [`docs/en/08-bot-server.md`](./docs/en/08-bot-server.md)
- Types, errors, and rate limit: [`docs/en/09-types-errors-rate-limit.md`](./docs/en/09-types-errors-rate-limit.md)
- CLI tool: [`docs/en/10-cli.md`](./docs/en/10-cli.md)

## Response Model (Important)

- Most APIs return `DataResponse`, with:
  - `resp.ok` (success when `code == 0`)
  - `resp.code` / `resp.msg`
  - `resp.data.xxx` or direct `resp.xxx` field access
  - `resp.to_dict()` to convert back to plain `dict`
- Strongly typed responses:
  - `BotService.get_info()` -> `BotInfoResponse` (`resp.bot.app_name`)
  - `MessageService.send_*()/reply_*()/get()` -> `MessageResponse` (`resp.message_id`, `resp.message.chat_id`)

```python
info = client.bot.get_info()
print(info.ok, info.bot.app_name)

spaces = wiki.list_spaces(page_size=10)
print(spaces.items)   # same as spaces.data.items
```

## Quick Start (Sync)

```python
from feishu_bot_sdk import FeishuClient, FeishuConfig, BitableService, DocxService

config = FeishuConfig(
    app_id="cli_xxx",
    app_secret="xxx",
    base_url="https://open.feishu.cn/open-apis",
    doc_url_prefix="https://your-tenant.feishu.cn/docx",
    doc_folder_token="fldcnxxx",   # optional
    member_permission="edit",      # view/edit/full_access
    rate_limit_enabled=True,       # enabled by default
)

client = FeishuClient(config)

# 1) Send message
client.send_text_message("ou_xxx", "open_id", "Hello from SDK")

# 2) CSV -> Bitable
bitable = BitableService(client)
app_token, app_url = bitable.create_from_csv("final.csv", "Task Result", "Result Table")
bitable.grant_edit_permission(app_token, "ou_xxx", "open_id")
print(app_url)

# 2.1) Generic record CRUD
record = bitable.create_record(app_token, "tbl_xxx", {"Task": "Follow up"})
bitable.update_record(app_token, "tbl_xxx", record.record.record_id, {"Task": "Done"})
for item in bitable.iter_records(app_token, "tbl_xxx", page_size=100):
    print(item.record_id)

# 3) Markdown -> Docx
docx = DocxService(client)
doc_id, doc_url = docx.create_document("Task Report")
docx.append_markdown(doc_id, "# Title\n\nBody text.")
docx.grant_edit_permission(doc_id, "ou_xxx", "open_id")
print(doc_url or doc_id)
```

## Async Example

```python
from feishu_bot_sdk import AsyncFeishuClient, AsyncBitableService, FeishuConfig

config = FeishuConfig(app_id="cli_xxx", app_secret="xxx")
client = AsyncFeishuClient(config)
bitable = AsyncBitableService(client)

await client.send_text_message("ou_xxx", "open_id", "hello async")
app_token, app_url = await bitable.create_from_csv("final.csv", "Async Result", "Sheet1")

await client.aclose()
```

## IM Message and Media

```python
from feishu_bot_sdk import FeishuClient, FeishuConfig, MediaService, MessageService

client = FeishuClient(FeishuConfig(app_id="cli_xxx", app_secret="xxx"))
message = MessageService(client)
media = MediaService(client)

sent = message.send_text(receive_id_type="open_id", receive_id="ou_xxx", text="hello")
image = media.upload_image("demo.png", image_type="message")
message.send_image(
    receive_id_type="open_id",
    receive_id="ou_xxx",
    image_key=image.image_key,
)

message.send_markdown(
    receive_id_type="open_id",
    receive_id="ou_xxx",
    markdown="### Daily Report\n\nTask done",
)
```

## Advanced IM Features

```python
from feishu_bot_sdk import MessageService

message = MessageService(client)
message.add_reaction("om_xxx", "SMILE")
message.pin_message("om_xxx")
message.send_urgent_app("om_xxx", user_id_list=["ou_xxx"], user_id_type="open_id")
batch = message.send_batch_message(
    msg_type="text",
    content={"text": "batch notification"},
    open_ids=["ou_xxx", "ou_yyy"],
)
print(batch.message_id)
```

## Event Models (Webhook / WS)

```python
from feishu_bot_sdk import FeishuEventRegistry

registry = FeishuEventRegistry()
registry.on_bitable_record_changed(lambda event: print(event.table_id, len(event.action_list)))
registry.on_bitable_field_changed(lambda event: print(event.table_id, event.revision))
```

## FeishuBotServer (Turnkey Long Connection Service)

```python
from feishu_bot_sdk import FeishuBotServer

server = FeishuBotServer(app_id="cli_xxx", app_secret="xxx")

@server.on_im_message_receive
def on_message(event):
    print("open_id:", event.sender_open_id, "text:", event.text)

@server.on_bot_menu
def on_menu(event):
    print("menu:", event.event_key)

# Handles SIGINT/SIGTERM and runs until process exit
server.run()
```

Management helpers:

- `await server.start()` / `await server.stop()`: async lifecycle control
- `await server.run_forever()`: keep WS listener running
- `server.status()`: runtime status, last event, counters, and last error
- `server.on_event(...)` / `server.on_default(...)`: generic event handlers

## Drive Files and Permissions

```python
from feishu_bot_sdk import DriveFileService, DrivePermissionService

drive = DriveFileService(client)
perm = DrivePermissionService(client)

uploaded = drive.upload_file("final.csv", parent_type="explorer", parent_node="fld_xxx")
print(uploaded.file_token)
task = drive.create_import_task(
    {
        "file_extension": "csv",
        "file_token": uploaded.file_token,
        "type": "bitable",
        "file_name": "Import Result",
        "point": {"mount_type": 1, "mount_key": "fld_xxx"},
    }
)
# Usually poll by get_import_task(task.ticket), then grant with the imported resource token.
perm.add_member(
    task.token,
    resource_type="bitable",
    member_id="ou_xxx",
    member_id_type="open_id",
    perm="edit",
)
```

## Wiki and Docs Content

```python
from feishu_bot_sdk import WikiService, DocContentService

wiki = WikiService(client)
docs = DocContentService(client)

spaces = wiki.list_spaces(page_size=10)
print(spaces.items)

results = wiki.search_nodes("weekly report", page_size=10)
print(results.items)

markdown = docs.get_markdown("doccn_xxx")
print(markdown[:200])
```

## Main Objects

- `FeishuClient` / `AsyncFeishuClient`: base Feishu API client
- `BitableService` / `AsyncBitableService`: Bitable features
- `DocxService` / `AsyncDocxService`: Docx features
- `DocxDocumentService` / `AsyncDocxDocumentService`: document info and paged block listing
- `DocxBlockService` / `AsyncDocxBlockService`: block CRUD, batch update, and content convert
- `DriveFileService` / `AsyncDriveFileService`: drive files, import/export, and media APIs
- `DrivePermissionService` / `AsyncDrivePermissionService`: members, public settings, password, and owner transfer
- `MessageService` / `AsyncMessageService`: message management
- `MediaService` / `AsyncMediaService`: media resources
- `FeishuBotServer`: long-connection server wrapper (handlers + lifecycle + status)

## Example Scripts

```bash
uv run python examples/sync_demo.py --receive-id ou_xxx --receive-id-type open_id
uv run python examples/async_demo.py --receive-id ou_xxx --receive-id-type open_id
uv run python examples/webhook_server.py
uv run python examples/ws_listener.py
uv run python examples/bot_server_demo.py
uv run python examples/card_callback.py
uv run python examples/im_media_demo.py --receive-id ou_xxx --receive-id-type open_id --image ./demo.png
uv run python examples/im_advanced_demo.py --receive-id ou_xxx --receive-id-type open_id --urgent-user-id ou_xxx
uv run python examples/drive_demo.py --resource-token doccn_xxx --resource-type docx --member-id ou_xxx
uv run python examples/wiki_docs_demo.py --search-keyword \"weekly report\" --doc-token doccn_xxx
```

Optional flags:

- `--csv final.csv`: demo for CSV -> Bitable
- `--markdown result.md`: demo for Markdown -> Docx

## Long Connection Notes

- One app supports up to 50 long connections.
- If multiple clients are online, events/callbacks are delivered to one random client (not broadcast).
