# feishu-bot-sdk

[English](./README_EN.md) | 中文

面向飞书机器人的轻量 Python SDK，提供：

- 飞书 access token 获取与缓存（`tenant` / `user` 双模式）
- IM 消息能力（发送/回复/编辑/撤回/转发/合并转发/reaction/pin/批量/加急/卡片）
- 群组管理（建群、查群、搜索、成员/管理员、发言权限、置顶消息、会话标签页、群菜单）
- 新版块式群公告（元数据、block 列表/子块读取、批量更新、插入、删除）
- CardKit 卡片实体（创建/流式更新/streaming_mode/配置更新）与卡片回调响应构造
- 图片、文件、消息资源上传下载
- 云空间文件/素材上传下载、导入导出任务
- Drive 权限管理（成员、公开设置、密码、owner transfer）
- 多维表格能力（CSV 导入 + 表/字段/记录 CRUD + batch + 分页迭代）
- Wiki 知识库（space/node/member/search/task）与云文档内容导出（`docs/v1/content`）
- 通讯录能力（用户/部门/授权范围查询 + 分页迭代）
- 日历能力（日历 CRUD、日程 CRUD、忙闲查询、CalDAV 配置）
- 邮箱能力（用户邮箱、邮件组、公共邮箱、地址状态、规则、事件订阅）
- 搜索能力（应用搜索、消息搜索、文档/Wiki 搜索）
- 云文档官方 convert/insert 写入、块级编辑、图片/附件替换
- 事件回调（Webhook）与长连接（WebSocket）
- 事件类型模型（IM、卡片、URL 预览、多维表格 record/field changed）
- IM 接收消息内容自动解析（按 `message_type` 输出强类型 `event.content`）
- 自适应限流器（按接口返回动态收敛/恢复）
- 同步 / 异步两套 API

## 安装

```bash
# pip
pip install feishu-bot-sdk

# uv
uv add feishu-bot-sdk

# 安装为全局命令行工具（推荐给 Agent 场景）
uv tool install feishu-bot-sdk
feishu --help
```

## CLI 用法（`feishu`）

- 命令名：`feishu`
- 默认输出：人类友好格式
- 机器可读输出：追加 `--format json`
- 认证优先级：环境变量优先，其次命令行全局参数
  - 环境变量：`FEISHU_APP_ID`、`FEISHU_APP_SECRET`、`FEISHU_AUTH_MODE`、`FEISHU_ACCESS_TOKEN`
  - 用户态变量：`FEISHU_USER_ACCESS_TOKEN`、`FEISHU_USER_REFRESH_TOKEN`
  - OAuth 交换变量：`FEISHU_APP_ACCESS_TOKEN`
  - Token Store：`FEISHU_PROFILE`、`FEISHU_TOKEN_STORE_PATH`、`FEISHU_NO_STORE`
  - 全局参数：`--app-id`、`--app-secret`、`--auth-mode`、`--access-token`、`--profile`、`--token-store`、`--no-store`

示例：

```bash
# 1) 获取当前认证模式 token（JSON 输出）
feishu auth token --format json

# 1.1) CLI User Auth（localhost 回调 + 自动落盘 token）
feishu auth login --scope "offline_access contact:user.base:readonly" --no-browser --format json
feishu auth whoami --format json
feishu auth refresh --format json
feishu auth logout --format json

# 1.2) 低层 OAuth 调试命令
feishu oauth authorize-url --redirect-uri https://example.com/callback --format json
feishu oauth exchange-code --code CODE --format json

# 2) 发送文本消息（默认人类友好输出）
feishu im send-text --receive-id ou_xxx --text "hello from cli"

# 3) 发送 Markdown 消息（从文件读取）
feishu im send-markdown --receive-id ou_xxx --markdown-file ./msg.md

# 3.1) 添加跟随气泡 / 转发话题 / 更新 URL 预览
feishu im push-follow-up om_xxx --follow-ups-json '[{"content":"继续处理"}]' --format json
feishu im forward-thread omt_xxx --receive-id-type chat_id --receive-id oc_xxx --format json
feishu im update-url-previews --preview-token token_1 --preview-token token_2 --open-id ou_xxx --format json

# 3.2) 群组与群公告
feishu chat list --all --format json
feishu chat create --chat-json '{"name":"Ops War Room","owner_id":"ou_xxx","user_id_list":["ou_xxx"],"chat_mode":"group","chat_type":"private"}' --user-id-type open_id --format json
feishu group member add --chat-id oc_xxx --member-id ou_xxx --member-id-type open_id --format json
feishu chat announcement get --chat-id oc_xxx --format json
feishu chat announcement list-blocks --chat-id oc_xxx --revision-id -1 --all --format json
feishu chat announcement batch-update --chat-id oc_xxx --requests-json '[{"update_text_elements":{"block_id":"doxxx","elements":[]}}]' --revision-id -1 --client-token token_1 --format json

# 4) 回复 Markdown（JSON 输出）
feishu im reply-markdown om_xxx --markdown "### 已收到" --format json

# 5) 上传图片
feishu media upload-image ./demo.png
# 5.1) 下载文件/图片；若是消息内资源需带 message_id
feishu media download-file file_xxx ./downloads/file.bin --format json
feishu media download-file img_v3_xxx ./downloads/image.jpg --message-id om_xxx --resource-type image --format json

# 6) CSV 创建多维表格并授权
feishu bitable create-from-csv ./final.csv --app-name "任务结果" --table-name "结果表" --grant-member-id ou_xxx
feishu bitable list-records --app-token app_xxx --table-id tbl_xxx --all --format json

# 7) 创建并写入 Docx
feishu docx create --title "日报" --folder-token fld_xxx --format json
feishu docx insert-content --document-id doccn_xxx --content-file ./report.md --content-type markdown --document-revision-id -1 --format json
feishu docx get-content --doc-token doccn_xxx --doc-type docx --content-type markdown --format json

# 8) 上传云空间文件
feishu drive upload-file ./final.csv --parent-type explorer --parent-node fld_xxx
feishu drive meta --request-docs-json '[{"doc_token":"doccn_xxx","doc_type":"docx"}]' --with-url true --format json
feishu drive grant-edit --token doccn_xxx --resource-type docx --member-id ou_xxx --permission edit --format json
feishu drive grant-edit --token doccn_xxx --resource-type docx --member-id me --permission edit --auth-mode user --format json

# 9) 搜索 Wiki 节点
feishu wiki search-nodes --query "项目周报" --all --format json

# 9.1) 搜索能力（应用 / 消息 / 文档/Wiki）
feishu search app --query "审批" --auth-mode user --format json
feishu search message --query "故障" --chat-type group_chat --auth-mode user --format json
feishu search doc-wiki --query "项目周报" --doc-filter-json '{"only_title": true}' --auth-mode user --format json

# 10) 通讯录查询
feishu contact user get --user-id ou_xxx --user-id-type open_id --format json
feishu contact department search --query "研发" --format json
feishu contact scope get --page-size 100 --format json

# 11) 日历查询与创建日程
feishu calendar list-calendars --page-size 50 --format json
feishu calendar create-event --calendar-id cal_xxx --event-file ./event.json --format json
feishu calendar attach-material --calendar-id cal_xxx --event-id evt_xxx --path ./agenda.md --format json

# 11.1) 邮箱能力
feishu mail address query-status --email ops@example.com --email alerts@example.com --format json
feishu mail message list --user-mailbox-id me --folder-id INBOX --all --format json
feishu mail message send-markdown --user-mailbox-id me --to-email user@example.com --subject "日报" --markdown-file ./report.md --format json
feishu mail mailbox alias create --user-mailbox-id me --email-alias alias@example.com --format json
feishu mail group create --mailgroup-json '{"email":"ops@example.com","name":"Ops Group"}' --format json
feishu mail public-mailbox member batch-create --public-mailbox-id support@example.com --items-file ./members.json --format json

# 12) 解析 webhook 事件信封
feishu webhook parse --body-file ./webhook.json --format json

# 13) 获取长连接 endpoint
feishu ws endpoint --format json

# 14) 启动长连接服务并打印事件
feishu server run --print-payload

# 15) 本地启动 webhook 回调服务（处理 10 个请求后自动退出）
feishu webhook serve --host 127.0.0.1 --port 8000 --path /webhook/feishu --max-requests 10

# 16) 后台启动 / 查询 / 停止长连接服务
feishu server start --pid-file ./.feishu_server.pid --log-file ./feishu-server.log
feishu server status --pid-file ./.feishu_server.pid --format json
feishu server stop --pid-file ./.feishu_server.pid

# 17) Agent 管道输入（stdin）
cat ./msg.md | feishu im send-markdown --receive-id ou_xxx --markdown-stdin --format json
```

## 模块文档

- 文档索引（中文）：[`docs/README.md`](./docs/README.md)
- 文档索引（英文）：[`docs/README_EN.md`](./docs/README_EN.md)
- 核心客户端与配置：[`docs/zh/01-core-client.md`](./docs/zh/01-core-client.md)
- IM 消息、群组与媒体：[`docs/zh/02-im.md`](./docs/zh/02-im.md)
- Drive 文件与权限：[`docs/zh/03-drive.md`](./docs/zh/03-drive.md)
- 多维表格（Bitable）：[`docs/zh/04-bitable.md`](./docs/zh/04-bitable.md)
- 云文档（Docx/Docs Content）：[`docs/zh/05-docx-and-docs.md`](./docs/zh/05-docx-and-docs.md)
- Wiki 知识库：[`docs/zh/06-wiki.md`](./docs/zh/06-wiki.md)
- 事件系统（Events/Webhook/WS）：[`docs/zh/07-events-webhook-ws.md`](./docs/zh/07-events-webhook-ws.md)
- FeishuBotServer 长连接服务：[`docs/zh/08-bot-server.md`](./docs/zh/08-bot-server.md)
- 类型、异常与限流：[`docs/zh/09-types-errors-rate-limit.md`](./docs/zh/09-types-errors-rate-limit.md)
- CLI 命令行工具：[`docs/zh/10-cli.md`](./docs/zh/10-cli.md)
- 日历（Calendar）：[`docs/zh/11-calendar.md`](./docs/zh/11-calendar.md)
- 通讯录（Contact）：[`docs/zh/12-contact.md`](./docs/zh/12-contact.md)
- 搜索（Search）：[`docs/zh/13-search.md`](./docs/zh/13-search.md)
- 云文档工作流速查：[`docs/zh/14-cloud-doc-workflows.md`](./docs/zh/14-cloud-doc-workflows.md)
- 邮箱（Mail）：[`docs/zh/15-mail.md`](./docs/zh/15-mail.md)

## 响应模型（重要）

- 大多数接口返回 `DataResponse`，支持：
  - `resp.ok`：是否成功（`code == 0`）
  - `resp.code` / `resp.msg`
  - `resp.data.xxx` 或 `resp.xxx` 访问数据字段
  - `resp.to_dict()` 转回普通 `dict`
- 典型强类型响应：
  - `BotService.get_info()` -> `BotInfoResponse`（`resp.bot.app_name`）
  - `MessageService.send_*()/reply_*()/get()` -> `MessageResponse`（`resp.message_id`、`resp.message.chat_id`）

```python
info = client.bot.get_info()
print(info.ok, info.bot.app_name)

spaces = wiki.list_spaces(page_size=10)
print(spaces.items)   # 等价于 spaces.data.items
```

## 1 分钟上手（同步）

```python
from feishu_bot_sdk import FeishuClient, FeishuConfig, BitableService, DocxService

config = FeishuConfig(
    app_id="cli_xxx",
    app_secret="xxx",
    base_url="https://open.feishu.cn/open-apis",
    doc_url_prefix="https://your-tenant.feishu.cn/docx",
    doc_folder_token="fldcnxxx",   # 可选
    member_permission="edit",      # view/edit/full_access
    rate_limit_enabled=True,       # 默认开启
)

client = FeishuClient(config)

# 1) 发消息
client.send_text_message("ou_xxx", "open_id", "你好，来自 SDK")

# 2) CSV -> Bitable
bitable = BitableService(client)
app_token, app_url = bitable.create_from_csv("final.csv", "任务结果", "结果表")
bitable.grant_edit_permission(app_token, "ou_xxx", "open_id")
print(app_url)

# 2.1) 通用记录 CRUD
record = bitable.create_record(app_token, "tbl_xxx", {"任务名称": "跟进客户"})
bitable.update_record(app_token, "tbl_xxx", record.record.record_id, {"任务名称": "已完成"})
for item in bitable.iter_records(app_token, "tbl_xxx", page_size=100):
    print(item.record_id)

# 3) Markdown / HTML -> Docx
docx = DocxService(client)
created = docx.create_document("任务报告")
doc_id = created["document_id"]
docx.insert_content(doc_id, "# 标题\n\n这是正文。", content_type="markdown")
docx.grant_edit_permission(doc_id, "ou_xxx", "open_id")
print(created["url"] or doc_id)
```

## 异步用法

```python
from feishu_bot_sdk import AsyncFeishuClient, AsyncBitableService, FeishuConfig

config = FeishuConfig(app_id="cli_xxx", app_secret="xxx")
client = AsyncFeishuClient(config)
bitable = AsyncBitableService(client)

await client.send_text_message("ou_xxx", "open_id", "hello async")
app_token, app_url = await bitable.create_from_csv("final.csv", "异步结果", "Sheet1")

await client.aclose()
```

## IM 消息、群组与媒体

```python
from feishu_bot_sdk import FeishuClient, FeishuConfig, MediaService, MessageService

client = FeishuClient(FeishuConfig(app_id="cli_xxx", app_secret="xxx"))
message = MessageService(client)
media = MediaService(client)

sent = message.send_text(receive_id_type="open_id", receive_id="ou_xxx", text="你好")
image = media.upload_image("demo.png", image_type="message")
message.send_image(
    receive_id_type="open_id",
    receive_id="ou_xxx",
    image_key=image.image_key,
)

message.send_markdown(
    receive_id_type="open_id",
    receive_id="ou_xxx",
    markdown="### 日报\n\n任务完成",
)
```

```python
from feishu_bot_sdk import ChatService

chat = ChatService(client)
announcement = chat.get_announcement("oc_xxx", user_id_type="open_id")
blocks = chat.list_announcement_blocks("oc_xxx", revision_id=-1, page_size=20)
print(announcement.get("announcement_type"), len(blocks.items))
```

## IM 高级能力

```python
from feishu_bot_sdk import MessageService

message = MessageService(client)
message.add_reaction("om_xxx", "SMILE")
message.pin_message("om_xxx")
message.send_urgent_app("om_xxx", user_id_list=["ou_xxx"], user_id_type="open_id")
batch = message.send_batch_message(
    msg_type="text",
    content={"text": "批量通知"},
    open_ids=["ou_xxx", "ou_yyy"],
)
print(batch.message_id)
```

## 事件模型（Webhook / WS）

```python
from feishu_bot_sdk import FeishuEventRegistry

registry = FeishuEventRegistry()
registry.on_bitable_record_changed(lambda event: print(event.table_id, len(event.action_list)))
registry.on_bitable_field_changed(lambda event: print(event.table_id, event.revision))
```

## FeishuBotServer（一站式长连接服务）

```python
from feishu_bot_sdk import FeishuBotServer

server = FeishuBotServer(app_id="cli_xxx", app_secret="xxx")

@server.on_im_message_receive
def on_message(event):
    print("open_id:", event.sender_open_id, "text:", event.text)

@server.on_bot_menu
def on_menu(event):
    print("menu:", event.event_key)

# 自动处理 SIGINT/SIGTERM，直到进程退出
server.run()
```

可用管理能力：

- `await server.start()` / `await server.stop()`：异步生命周期控制
- `await server.run_forever()`：长连接常驻运行
- `server.status()`：查看运行状态、最近事件、事件计数、最后错误
- `server.on_event(...)` / `server.on_default(...)`：注册通用事件回调

## Drive 文件与权限

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
        "file_name": "导入结果",
        "point": {"mount_type": 1, "mount_key": "fld_xxx"},
    }
)
# 一般先通过 get_import_task(task.ticket) 轮询完成，再取导入结果资源 token 进行授权
perm.add_member(
    task.token,
    resource_type="bitable",
    member_id="ou_xxx",
    member_id_type="open_id",
    perm="edit",
)
```

## Wiki 与云文档内容

```python
from feishu_bot_sdk import WikiService, DocContentService

wiki = WikiService(client)
docs = DocContentService(client)

spaces = wiki.list_spaces(page_size=10)
print(spaces.items)

results = wiki.search_nodes("项目周报", page_size=10)
print(results.items)

markdown = docs.get_markdown("doccn_xxx")
print(markdown[:200])
```

## 群组（Chat）

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

## 日历（Calendar）

```python
from feishu_bot_sdk import CalendarService

calendar = CalendarService(client)
primary = calendar.primary_calendar()
print(primary.calendar.calendar_id)

events = calendar.list_events(primary.calendar.calendar_id, page_size=10)
print(events.items)
```

## 通讯录（Contact）

```python
from feishu_bot_sdk import ContactService

contact = ContactService(client)
profile = contact.get_user("ou_xxx", user_id_type="open_id")
print(profile.user.name)

for item in contact.iter_users_by_department("od_xxx", page_size=50):
    print(item.get("open_id"))
```

## 搜索（Search）

```python
from feishu_bot_sdk import SearchService

search = SearchService(client)
apps = search.search_apps("审批", page_size=10)
print(apps.items)

messages = search.search_messages("故障", chat_type="group_chat", page_size=20)
print(messages.items)

docs = search.search_doc_wiki("项目周报", doc_filter={"only_title": True}, page_size=20)
print(docs.res_units)
```

## 邮箱（Mail）

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
    subject="日报",
    to=["user@example.com"],
    markdown="# 日报\n\n任务已完成\n\n![架构图](https://cdn.example.com/diagram.png)",
)

group = MailGroupService(client)
created = group.create_mailgroup({"email": "ops@example.com", "name": "Ops Group"})
print(created.mailgroup_id)

public = PublicMailboxService(client)
mailboxes = public.list_public_mailboxes(page_size=20)
print(mailboxes.items)
```

## 核心对象

- `FeishuClient` / `AsyncFeishuClient`：飞书 API 基础客户端
- `BitableService` / `AsyncBitableService`：多维表格能力
- `DocxService` / `AsyncDocxService`：文档能力
- `DocxDocumentService` / `AsyncDocxDocumentService`：文档信息与分页获取文档块
- `DocxBlockService` / `AsyncDocxBlockService`：块 CRUD、批量更新与内容转换
- `DriveFileService` / `AsyncDriveFileService`：云空间文件、导入导出、素材接口
- `DrivePermissionService` / `AsyncDrivePermissionService`：成员、公开设置、密码与 owner transfer
- `ChatService` / `AsyncChatService`：群组、群公告、成员/管理员、群菜单、会话标签页
- `CalendarService` / `AsyncCalendarService`：日历、日程、忙闲和 CalDAV 配置
- `ContactService` / `AsyncContactService`：通讯录用户、部门、授权范围
- `MailMailboxService` / `AsyncMailMailboxService`、`MailMessageService` / `AsyncMailMessageService`、`MailFolderService` / `AsyncMailFolderService`、`MailContactService` / `AsyncMailContactService`、`MailRuleService` / `AsyncMailRuleService`、`MailEventService` / `AsyncMailEventService`、`MailAddressService` / `AsyncMailAddressService`：用户邮箱、邮件、文件夹、联系人、规则、事件订阅、地址状态
- `MailGroupService` / `AsyncMailGroupService`、`MailGroupAliasService` / `AsyncMailGroupAliasService`、`MailGroupMemberService` / `AsyncMailGroupMemberService`、`MailGroupPermissionMemberService` / `AsyncMailGroupPermissionMemberService`、`MailGroupManagerService` / `AsyncMailGroupManagerService`：邮件组、别名、成员、权限成员、管理员
- `PublicMailboxService` / `AsyncPublicMailboxService`、`PublicMailboxAliasService` / `AsyncPublicMailboxAliasService`、`PublicMailboxMemberService` / `AsyncPublicMailboxMemberService`：公共邮箱、别名、成员
- `SearchService` / `AsyncSearchService`：应用、消息、文档/Wiki 搜索
- `MessageService` / `AsyncMessageService`：消息管理
- `CardKitService` / `AsyncCardKitService`：CardKit 卡片实体创建、流式更新、配置管理
- `MediaService` / `AsyncMediaService`：媒体资源
- `FeishuBotServer`：长连接服务封装（回调注册 + 启停 + 状态管理）

## 示例脚本

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
uv run python examples/wiki_docs_demo.py --search-keyword 项目周报 --doc-token doccn_xxx
```

可选参数：

- `--csv final.csv`：演示 CSV 导入 Bitable
- `--markdown result.md`：演示 Markdown 追加到 Docx

## 长连接注意事项

- 同一个应用实例支持最多 50 条长连接。
- 多个 client 同时在线时，事件/回调是随机投递到其中一个 client，不是广播模式。
