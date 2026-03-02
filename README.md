# feishu-bot-sdk

面向飞书机器人的轻量 Python SDK，提供：

- 飞书 access token 获取与缓存（`tenant` / `user` 双模式）
- IM 消息能力（发送/回复/编辑/撤回/转发/合并转发/reaction/pin/批量/加急/卡片）
- 图片、文件、消息资源上传下载
- 云空间文件/素材上传下载、导入导出任务
- Drive 权限管理（成员、公开设置、密码、owner transfer）
- 多维表格能力（CSV 导入 + 表/字段/记录 CRUD + batch + 分页迭代）
- Wiki 知识库（space/node/member/search/task）与云文档内容导出（`docs/v1/content`）
- 日历能力（日历 CRUD、日程 CRUD、忙闲查询、CalDAV 配置）
- Markdown 追加写入 Docx
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
  - 全局参数：`--app-id`、`--app-secret`、`--auth-mode`、`--access-token`

示例：

```bash
# 1) 获取当前认证模式 token（JSON 输出）
feishu auth token --format json

# 1.1) OAuth 授权与换取用户 token
feishu oauth authorize-url --redirect-uri https://example.com/callback --format json
feishu oauth exchange-code --code CODE --format json

# 2) 发送文本消息（默认人类友好输出）
feishu im send-text --receive-id ou_xxx --text "hello from cli"

# 3) 发送 Markdown 消息（从文件读取）
feishu im send-markdown --receive-id ou_xxx --markdown-file ./msg.md

# 4) 回复 Markdown（JSON 输出）
feishu im reply-markdown om_xxx --markdown "### 已收到" --format json

# 5) 上传图片
feishu media upload-image ./demo.png

# 6) CSV 创建多维表格并授权
feishu bitable create-from-csv ./final.csv --app-name "任务结果" --table-name "结果表" --grant-member-id ou_xxx

# 7) 创建并写入 Docx
feishu docx create-from-markdown --title "日报" --markdown-file ./report.md

# 8) 上传云空间文件
feishu drive upload-file ./final.csv --parent-type explorer --parent-node fld_xxx

# 9) 搜索 Wiki 节点
feishu wiki search-nodes --query "项目周报" --format json

# 10) 日历查询与创建日程
feishu calendar list-calendars --page-size 50 --format json
feishu calendar create-event --calendar-id cal_xxx --event-file ./event.json --format json
feishu calendar attach-material --calendar-id cal_xxx --event-id evt_xxx --path ./agenda.md --format json

# 11) 解析 webhook 事件信封
feishu webhook parse --body-file ./webhook.json --format json

# 12) 获取长连接 endpoint
feishu ws endpoint --format json

# 13) 启动长连接服务并打印事件
feishu server run --print-payload

# 14) 本地启动 webhook 回调服务（处理 10 个请求后自动退出）
feishu webhook serve --host 127.0.0.1 --port 8000 --path /webhook/feishu --max-requests 10

# 15) 后台启动 / 查询 / 停止长连接服务
feishu server start --pid-file ./.feishu_server.pid --log-file ./feishu-server.log
feishu server status --pid-file ./.feishu_server.pid --format json
feishu server stop --pid-file ./.feishu_server.pid

# 16) Agent 管道输入（stdin）
cat ./msg.md | feishu im send-markdown --receive-id ou_xxx --markdown-stdin --format json
```

## 模块文档

- 文档索引（中文）：[`docs/README.md`](./docs/README.md)
- 文档索引（英文）：[`docs/README_EN.md`](./docs/README_EN.md)
- 核心客户端与配置：[`docs/zh/01-core-client.md`](./docs/zh/01-core-client.md)
- IM 消息与媒体：[`docs/zh/02-im.md`](./docs/zh/02-im.md)
- Drive 文件与权限：[`docs/zh/03-drive.md`](./docs/zh/03-drive.md)
- 多维表格（Bitable）：[`docs/zh/04-bitable.md`](./docs/zh/04-bitable.md)
- 云文档（Docx/Docs Content）：[`docs/zh/05-docx-and-docs.md`](./docs/zh/05-docx-and-docs.md)
- Wiki 知识库：[`docs/zh/06-wiki.md`](./docs/zh/06-wiki.md)
- 事件系统（Events/Webhook/WS）：[`docs/zh/07-events-webhook-ws.md`](./docs/zh/07-events-webhook-ws.md)
- FeishuBotServer 长连接服务：[`docs/zh/08-bot-server.md`](./docs/zh/08-bot-server.md)
- 类型、异常与限流：[`docs/zh/09-types-errors-rate-limit.md`](./docs/zh/09-types-errors-rate-limit.md)
- CLI 命令行工具：[`docs/zh/10-cli.md`](./docs/zh/10-cli.md)
- 日历（Calendar）：[`docs/zh/11-calendar.md`](./docs/zh/11-calendar.md)

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

# 3) Markdown -> Docx
docx = DocxService(client)
doc_id, doc_url = docx.create_document("任务报告")
docx.append_markdown(doc_id, "# 标题\n\n这是正文。")
docx.grant_edit_permission(doc_id, "ou_xxx", "open_id")
print(doc_url or doc_id)
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

## IM 消息与媒体

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

## 日历（Calendar）

```python
from feishu_bot_sdk import CalendarService

calendar = CalendarService(client)
primary = calendar.primary_calendar()
print(primary.calendar.calendar_id)

events = calendar.list_events(primary.calendar.calendar_id, page_size=10)
print(events.items)
```

## 核心对象

- `FeishuClient` / `AsyncFeishuClient`：飞书 API 基础客户端
- `BitableService` / `AsyncBitableService`：多维表格能力
- `DocxService` / `AsyncDocxService`：文档能力
- `DocxDocumentService` / `AsyncDocxDocumentService`：文档信息与分页获取文档块
- `DocxBlockService` / `AsyncDocxBlockService`：块 CRUD、批量更新与内容转换
- `DriveFileService` / `AsyncDriveFileService`：云空间文件、导入导出、素材接口
- `DrivePermissionService` / `AsyncDrivePermissionService`：成员、公开设置、密码与 owner transfer
- `CalendarService` / `AsyncCalendarService`：日历、日程、忙闲和 CalDAV 配置
- `MessageService` / `AsyncMessageService`：消息管理
- `MediaService` / `AsyncMediaService`：媒体资源
- `FeishuBotServer`：长连接服务封装（回调注册 + 启停 + 状态管理）

英文说明见 `README_EN.md`。

## 示例脚本

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
uv run python examples/wiki_docs_demo.py --search-keyword 项目周报 --doc-token doccn_xxx
```

可选参数：

- `--csv final.csv`：演示 CSV 导入 Bitable
- `--markdown result.md`：演示 Markdown 追加到 Docx

## 长连接注意事项

- 同一个应用实例支持最多 50 条长连接。
- 多个 client 同时在线时，事件/回调是随机投递到其中一个 client，不是广播模式。
