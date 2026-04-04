# feishu-bot-sdk

English | [中文](./README.md)

A lightweight Python SDK for Feishu bot integrations, including:

- Access token retrieval and caching for both `tenant` and `user` modes
- IM messaging (send/reply/edit/recall/forward/merge-forward/reaction/pin/batch/urgent/cards)
- Chat management (create/get/search/list chats, members/managers, moderation, top notice, tabs, and menu)
- Block-based announcements (metadata, block listing/children traversal, batch update, insert, delete)
- CardKit card entities (create/streaming update/streaming_mode/settings) and card callback response helpers
- Image/file/message-resource upload and download
- Drive file/media upload & download with import/export tasks
- Drive permissions (members, public settings, password, owner transfer)
- Bitable features (CSV import + table/field/record CRUD + batch + pagination iterators)
- Wiki APIs (space/node/member/search/task) and Docs content export (`docs/v1/content`)
- Contact APIs (user/department/scope query + pagination iterators)
- Calendar APIs (calendar/event CRUD, freebusy, CalDAV config)
- Task APIs (task/tasklist/subtask/comment CRUD, member management, reminders, and shortcut workflows)
- Mail APIs (user mailboxes, drafts, threads, mail groups, public mailboxes, address status, rules, event subscription)
- Minutes APIs (minute metadata and media download URL retrieval)
- Search APIs (app search, message search, doc/wiki search)
- Official Docx convert/insert writes, block editing, and image/file replacement
- Webhook callbacks and long connections (WebSocket)
- Typed event models (IM/card/URL preview/Bitable record & field changed)
- Automatic typed parsing for incoming IM content (`event.content` by `message_type`)
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
- Auth priority: environment variables > global flags > CLI profile > local token store profile
  - Env: `FEISHU_APP_ID`, `FEISHU_APP_SECRET`, `FEISHU_AUTH_MODE`, `FEISHU_ACCESS_TOKEN`
  - User env: `FEISHU_USER_ACCESS_TOKEN`, `FEISHU_USER_REFRESH_TOKEN`
  - OAuth exchange env: `FEISHU_APP_ACCESS_TOKEN`
  - CLI config / store: `FEISHU_PROFILE`, `FEISHU_CLI_CONFIG_PATH`, `FEISHU_SECRET_STORE_PATH`, `FEISHU_SECRET_STORE_KEY_PATH`, `FEISHU_TOKEN_STORE_PATH`, `FEISHU_NO_STORE`
  - Flags: `--app-id`, `--app-secret`, `--as`, `--access-token`, `--profile`, `--token-store`, `--no-store`
- `--app-secret` is still supported, but only recommended for temporary debugging; prefer `feishu config init --app-secret-stdin`

Examples:

```bash
# 0) Initialize a CLI profile (recommended)
printf 'app_secret' | feishu config init --profile default --app-id cli_xxx --app-secret-stdin --set-default --as auto --format json
feishu config show --format json
feishu config list-profiles --format json
feishu config migrate-token-store --source-path ~/.config/feishu-bot-sdk/tokens.json --app-id cli_xxx --format json

# 1) Get token for current auth mode (JSON output)
feishu auth token --format json

# 1.1) CLI User Auth (localhost callback + token persistence)
feishu auth login --scope "offline_access contact:user.base:readonly" --no-browser --format json
feishu auth whoami --format json
feishu auth refresh --format json
feishu auth logout --format json

# 1.2) Low-level OAuth debug commands
feishu oauth authorize-url --redirect-uri https://example.com/callback --format json
feishu oauth exchange-code --code CODE --format json

# 2) Send text message (human output by default)
feishu im send-text --receive-id ou_xxx --text "hello from cli"

# 3) Send markdown from file
feishu im send-markdown --receive-id ou_xxx --markdown-file ./msg.md

# 3.1) Push follow-up / forward thread / update URL previews
feishu im push-follow-up om_xxx --follow-ups-json '[{"content":"continue"}]' --format json
feishu im forward-thread omt_xxx --receive-id-type chat_id --receive-id oc_xxx --format json
feishu im update-url-previews --preview-token token_1 --preview-token token_2 --open-id ou_xxx --format json

# 3.2) Chats and announcements
feishu chat list --all --format json
feishu chat create --chat-json '{"name":"Ops War Room","owner_id":"ou_xxx","user_id_list":["ou_xxx"],"chat_mode":"group","chat_type":"private"}' --user-id-type open_id --format json
feishu group member add --chat-id oc_xxx --member-id ou_xxx --member-id-type open_id --format json
feishu chat announcement get --chat-id oc_xxx --format json
feishu chat announcement list-blocks --chat-id oc_xxx --revision-id -1 --all --format json
feishu chat announcement batch-update --chat-id oc_xxx --requests-json '[{"update_text_elements":{"block_id":"doxxx","elements":[]}}]' --revision-id -1 --client-token token_1 --format json

# 4) Reply markdown (JSON output)
feishu im reply-markdown om_xxx --markdown "### received" --format json

# 5) Upload image
feishu media upload-image ./demo.png
# 5.1) Download file/image; for user-sent message resources include message_id
feishu media download-file file_xxx ./downloads/file.bin --format json
feishu media download-file img_v3_xxx ./downloads/image.jpg --message-id om_xxx --resource-type image --format json

# 6) Create Bitable from CSV and grant access
feishu bitable create-from-csv ./final.csv --app-name "Task Result" --table-name "Result" --grant-member-id ou_xxx
# 6.1) List tables first; some commands can omit --table-id when the app has a default or only one table
feishu bitable list-tables --app-token app_xxx --format json
feishu bitable list-records --app-token app_xxx --table-id tbl_xxx --all --format json
feishu bitable list-views --app-token app_xxx --format json

# 7) Create and write Docx
feishu docx create --title "Daily Report" --folder-token fld_xxx --format json
feishu docx +insert-content --document-id doccn_xxx --content-file ./report.md --content-type markdown --document-revision-id -1 --format json
feishu docx get-content --doc-token doccn_xxx --doc-type docx --content-type markdown --format json

In `--content-file` mode, `docx +insert-content` resolves relative local image paths against the source Markdown file directory.

# 8) Upload file to Drive
feishu drive root-folder-meta --as user --format json
feishu drive create-folder --as user --folder-token <root_token> --name "Uploads" --format json
feishu drive +import --file ./draft.md --type docx --format json
feishu drive +export --token doccn_xxx --doc-type docx --file-extension pdf --output-dir ./exports --format json
feishu drive +move --file-token fld_src --type folder --folder-token fld_dst --format json
feishu drive +task_result --scenario export --ticket ticket_xxx --file-token doccn_xxx --format json
feishu drive upload-file ./final.csv --parent-type explorer --parent-node fld_xxx
feishu drive upload-file ./final.csv --parent-type explorer --parent-node fld_xxx --as user --check-requester-owner --format json
feishu drive meta --request-docs-json '[{"doc_token":"doccn_xxx","doc_type":"docx"}]' --with-url true --format json
feishu drive meta --request-docs-json '[{"doc_token":"file_xxx","doc_type":"file"}]' --as user --check-requester-owner --format json
feishu drive grant-edit --token doccn_xxx --resource-type docx --member-id ou_xxx --permission edit --format json
feishu drive grant-edit --token doccn_xxx --resource-type docx --member-id me --permission edit --as user --format json

# 9) Search wiki nodes
feishu wiki search-nodes --query "weekly report" --all --format json

# 9.1) Search APIs (apps/messages/docs-wiki)
feishu search app --query "approval" --as user --format json
feishu search message --query "incident" --chat-type group_chat --as user --format json
feishu search doc-wiki --query "weekly report" --doc-filter-json '{"only_title": true}' --as user --format json

# 10) Contact queries
feishu contact user get --user-id ou_xxx --user-id-type open_id --format json
feishu contact department search --query "engineering" --format json
feishu contact scope get --page-size 100 --format json

# 11) Calendar query and create event
feishu calendar list-calendars --page-size 50 --format json
feishu calendar create-event --calendar-id cal_xxx --event-file ./event.json --format json
feishu calendar +attach-material ./agenda.md --calendar-id cal_xxx --event-id evt_xxx --format json
feishu calendar +rsvp --event-id evt_xxx --rsvp-status accept --format json

# 11.1) Mail APIs
feishu mail address query-status --email ops@example.com --email alerts@example.com --format json
feishu mail message list --user-mailbox-id me --folder-id INBOX --all --format json
feishu mail +send-markdown --user-mailbox-id me --to-email user@example.com --subject "Daily Report" --markdown-file ./report.md --format json
feishu mail +draft-create --user-mailbox-id me --raw-file ./draft.eml --format json
feishu mail +draft-edit --user-mailbox-id me --draft-id draft_xxx --raw-file ./draft-updated.eml --format json
feishu mail +thread --user-mailbox-id me --thread-id th_xxx --thread-format metadata --format json
feishu mail mailbox alias create --user-mailbox-id me --email-alias alias@example.com --format json
feishu mail group create --mailgroup-json '{"email":"ops@example.com","name":"Ops Group"}' --format json
feishu mail public-mailbox member batch-create --public-mailbox-id support@example.com --items-file ./members.json --format json

# 11.2) Minutes APIs
feishu minutes get --params '{"minute_token":"obcnq3b9jl72l83w4f14xxxx"}' --format json
feishu minutes +download --minute-tokens obcnq3b9jl72l83w4f14xxxx --url-only --format json

# 11.3) Task APIs
feishu task +create --summary "Follow up contract" --assignee ou_xxx --due +2d --format json
feishu task +comment --task-id task_xxx --content "Customer contacted" --format json
feishu task +delete --task-id task_xxx --format json
feishu task +complete --task-id task_xxx --format json
feishu task +reopen --task-id task_xxx --format json
feishu task +assign --task-id task_xxx --add ou_xxx,ou_yyy --format json
feishu task +followers --task-id task_xxx --add ou_xxx --format json
feishu task +reminder --task-id task_xxx --set 1h --format json
feishu task +get-my-tasks --as user --query "contract" --page-all --format json

# 12) Parse webhook envelope
feishu webhook parse --body-file ./webhook.json --format json

# 13) Fetch long-connection endpoint
feishu ws endpoint --format json

# 14) Run long-connection server and print events
feishu server run --print-payload

# 15) Run local webhook server (auto-stop after 10 requests)
feishu webhook serve --host 127.0.0.1 --port 8000 --path /webhook/feishu --max-requests 10

# 16) Start / check / stop long-connection service in background
feishu server start --pid-file ./.feishu_server.pid --log-file ./feishu-server.log
feishu server status --pid-file ./.feishu_server.pid --format json
feishu server stop --pid-file ./.feishu_server.pid

# 17) Agent pipeline input (stdin)
cat ./msg.md | feishu im send-markdown --receive-id ou_xxx --markdown-stdin --format json
```

## Module Docs

- Docs index (Chinese): [`docs/README.md`](./docs/README.md)
- Docs index (English): [`docs/README_EN.md`](./docs/README_EN.md)
- Core client and config: [`docs/en/01-core-client.md`](./docs/en/01-core-client.md)
- IM messaging, chats, and media: [`docs/en/02-im.md`](./docs/en/02-im.md)
- Drive files and permissions: [`docs/en/03-drive.md`](./docs/en/03-drive.md)
- Bitable: [`docs/en/04-bitable.md`](./docs/en/04-bitable.md)
- Docx and Docs content: [`docs/en/05-docx-and-docs.md`](./docs/en/05-docx-and-docs.md)
- Wiki: [`docs/en/06-wiki.md`](./docs/en/06-wiki.md)
- Event system (Events/Webhook/WS): [`docs/en/07-events-webhook-ws.md`](./docs/en/07-events-webhook-ws.md)
- FeishuBotServer long-connection service: [`docs/en/08-bot-server.md`](./docs/en/08-bot-server.md)
- Types, errors, and rate limit: [`docs/en/09-types-errors-rate-limit.md`](./docs/en/09-types-errors-rate-limit.md)
- CLI tool: [`docs/en/10-cli.md`](./docs/en/10-cli.md)
- Calendar: [`docs/en/11-calendar.md`](./docs/en/11-calendar.md)
- Contact: [`docs/en/12-contact.md`](./docs/en/12-contact.md)
- Search: [`docs/en/13-search.md`](./docs/en/13-search.md)
- Cloud doc workflows: [`docs/en/14-cloud-doc-workflows.md`](./docs/en/14-cloud-doc-workflows.md)
- Mail: [`docs/en/15-mail.md`](./docs/en/15-mail.md)

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

# 3) Markdown / HTML -> Docx
docx = DocxService(client)
created = docx.create_document("Task Report")
doc_id = created["document_id"]
docx.insert_content(doc_id, "# Title\n\nBody text.", content_type="markdown")
docx.grant_edit_permission(doc_id, "ou_xxx", "open_id")
print(created["url"] or doc_id)
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

## IM Messaging, Chats, and Media

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

```python
from feishu_bot_sdk import ChatService

chat = ChatService(client)
announcement = chat.get_announcement("oc_xxx", user_id_type="open_id")
blocks = chat.list_announcement_blocks("oc_xxx", revision_id=-1, page_size=20)
print(announcement.get("announcement_type"), len(blocks.items))
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

## Chats

```python
from feishu_bot_sdk import ChatService

chat = ChatService(client)

groups = chat.list_chats(user_id_type="open_id", page_size=10)
print(groups.items)

announcement = chat.get_announcement("oc_xxx", user_id_type="open_id")
print(announcement.get("announcement_type"), announcement.get("revision_id"))

blocks = chat.list_announcement_blocks("oc_xxx", revision_id=-1, page_size=20)
print(blocks.items)
```

## Calendar

```python
from feishu_bot_sdk import CalendarService

calendar = CalendarService(client)
primary = calendar.primary_calendar()
print(primary.calendar.calendar_id)

events = calendar.list_events(primary.calendar.calendar_id, page_size=10)
print(events.items)
```

## Contact

```python
from feishu_bot_sdk import ContactService

contact = ContactService(client)
profile = contact.get_user("ou_xxx", user_id_type="open_id")
print(profile.user.name)

for item in contact.iter_users_by_department("od_xxx", page_size=50):
    print(item.get("open_id"))
```

## Search

```python
from feishu_bot_sdk import SearchService

search = SearchService(client)
apps = search.search_apps("approval", page_size=10)
print(apps.items)

messages = search.search_messages("incident", chat_type="group_chat", page_size=20)
print(messages.items)

docs = search.search_doc_wiki("weekly report", doc_filter={"only_title": True}, page_size=20)
print(docs.res_units)
```

## Mail

```python
from feishu_bot_sdk import (
    MailAddressService,
    MailGroupService,
    MailMessageService,
    PublicMailboxService,
)

address = MailAddressService(client)
print(address.query_status(["ops@example.com"]).user_list)

message = MailMessageService(client)
inbox = message.list_messages("me", folder_id="INBOX", page_size=20)
print(inbox.items)

message.send_markdown(
    "me",
    subject="Daily Report",
    to=["user@example.com"],
    markdown="# Daily Report\n\nTask completed\n\n![Diagram](https://cdn.example.com/diagram.png)",
)

group = MailGroupService(client)
created = group.create_mailgroup({"email": "ops@example.com", "name": "Ops Group"})
print(created.mailgroup_id)

public = PublicMailboxService(client)
mailboxes = public.list_public_mailboxes(page_size=20)
print(mailboxes.items)
```

## Main Objects

- `FeishuClient` / `AsyncFeishuClient`: base Feishu API client
- `BitableService` / `AsyncBitableService`: Bitable features
- `DocxService` / `AsyncDocxService`: Docx features
- `DocxDocumentService` / `AsyncDocxDocumentService`: document info and paged block listing
- `DocxBlockService` / `AsyncDocxBlockService`: block CRUD, batch update, and content convert
- `DriveFileService` / `AsyncDriveFileService`: drive files, import/export, and media APIs
- `DrivePermissionService` / `AsyncDrivePermissionService`: members, public settings, password, and owner transfer
- `ChatService` / `AsyncChatService`: chats, announcements, members/managers, menu, and chat tabs
- `CalendarService` / `AsyncCalendarService`: calendars, events, freebusy, and CalDAV config
- `ContactService` / `AsyncContactService`: contact users, departments, and scopes
- `MailMailboxService` / `AsyncMailMailboxService`, `MailMessageService` / `AsyncMailMessageService`, `MailDraftService` / `AsyncMailDraftService`, `MailThreadService` / `AsyncMailThreadService`, `MailFolderService` / `AsyncMailFolderService`, `MailContactService` / `AsyncMailContactService`, `MailRuleService` / `AsyncMailRuleService`, `MailEventService` / `AsyncMailEventService`, `MailAddressService` / `AsyncMailAddressService`: user mailboxes, messages, drafts, threads, folders, contacts, rules, event subscription, and address status
- `MailGroupService` / `AsyncMailGroupService`, `MailGroupAliasService` / `AsyncMailGroupAliasService`, `MailGroupMemberService` / `AsyncMailGroupMemberService`, `MailGroupPermissionMemberService` / `AsyncMailGroupPermissionMemberService`, `MailGroupManagerService` / `AsyncMailGroupManagerService`: mail groups, aliases, members, permission members, and managers
- `PublicMailboxService` / `AsyncPublicMailboxService`, `PublicMailboxAliasService` / `AsyncPublicMailboxAliasService`, `PublicMailboxMemberService` / `AsyncPublicMailboxMemberService`: public mailboxes, aliases, and members
- `MinutesService` / `AsyncMinutesService`: minute metadata and media download URL helpers
- `SearchService` / `AsyncSearchService`: app, message, and doc/wiki search
- `MessageService` / `AsyncMessageService`: message management
- `CardKitService` / `AsyncCardKitService`: CardKit card entity create, streaming update, settings
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
uv run python examples/cardkit_streaming_demo.py
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
