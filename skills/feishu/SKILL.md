---
name: feishu
description: >
  飞书（Lark）开放平台 Python SDK 和 CLI 工具使用指南。
  当用户需要处理任何飞书相关任务时触发此 skill，包括但不限于：
  (1) 飞书消息发送（文本、Markdown、图片、卡片），
  (2) 飞书 CardKit 卡片实体（创建、流式更新、streaming_mode、回调响应），
  (2) 飞书云文档操作（创建、编辑、导出文档内容），
  (3) 飞书多维表格/Bitable（创建表格、CSV导入、记录增删改查），
  (4) 飞书云盘/Drive（文件上传下载、权限管理），
  (5) 飞书知识库/Wiki（搜索、空间管理），
  (6) 飞书日历/Calendar（日程创建、查询、附件），
  (7) 飞书通讯录/Contact（用户、部门查询），
  (8) 飞书搜索（应用、消息、文档搜索），
  (9) 飞书机器人开发（Webhook、WebSocket 事件处理），
  (10) 任何涉及 `feishu` CLI 命令或 `feishu_bot_sdk` Python 导入的任务。
  即使用户没有明确提到 feishu-bot-sdk，只要任务涉及飞书平台的 API 操作、
  飞书文档处理、飞书数据管理、飞书自动化，都应使用此 skill。
---

# feishu-bot-sdk

飞书开放平台 Python SDK + CLI。提供 `feishu` 命令行工具和 Python 同步/异步 API。

## 环境变量配置（优先级最高）

CLI 认证优先级：环境变量 > CLI 参数 > 本地 token store。

使用前先确认环境变量是否已设置，如果已设置则无需传递 `--app-id` / `--app-secret` 等参数：

```bash
# 核心凭证（必需）
export FEISHU_APP_ID="cli_xxx"
export FEISHU_APP_SECRET="xxx"

# 认证模式（可选，默认 tenant）
export FEISHU_AUTH_MODE="tenant"        # tenant 或 user

# 静态 token（可选，跳过自动认证）
export FEISHU_ACCESS_TOKEN="t-xxx"

# 用户认证 token（auth_mode=user 时使用）
export FEISHU_USER_ACCESS_TOKEN="u-xxx"
export FEISHU_USER_REFRESH_TOKEN="ur-xxx"

# OAuth 交换用 token
export FEISHU_APP_ACCESS_TOKEN="a-xxx"

# Token 存储配置
export FEISHU_PROFILE="default"
export FEISHU_TOKEN_STORE_PATH="/path/to/tokens.json"
export FEISHU_NO_STORE="1"              # 禁用本地 token 存储

# 兼容变量
export APP_ID="cli_xxx"
export APP_SECRET="xxx"
```

当环境变量已配置时，CLI 命令可以省略凭证参数直接使用：
```bash
feishu im send-text --receive-id ou_xxx --text "hello"
```

## 安装

```bash
pip install feishu-bot-sdk
# 或作为全局 CLI 工具：
uv tool install feishu-bot-sdk
```

## CLI 命令速查

全局参数：`--format human|json`、`--app-id`、`--app-secret`、`--auth-mode tenant|user`、`--base-url`、`--timeout`

所有命令支持 `--format json` 输出机器可读格式，支持 stdin 输入（`--*-stdin`、`--*-file`、`--*-json`）。

### 命令组总览

| 命令组 | 用途 | 示例 |
|--------|------|------|
| `auth` | 认证、获取 token、原始 API 请求 | `feishu auth token --format json` |
| `oauth` | OAuth 授权流程 | `feishu oauth authorize-url --format json` |
| `bot` | 机器人信息 | `feishu bot info --format json` |
| `im` | 消息发送/回复/撤回/转发 | `feishu im send-text --receive-id ou_xxx --text "hello"` |
| `media` | 图片/文件上传下载 | `feishu media upload-image photo.png` |
| `bitable` | 多维表格 CRUD | `feishu bitable create-from-csv data.csv --app-name "App" --table-name "Sheet1"` |
| `docx` | 云文档创建/编辑/导出 | `feishu docx create --title "Report"` |
| `drive` | 云盘文件/权限管理 | `feishu drive upload-file report.pdf --parent-type explorer --parent-node fld_xxx` |
| `wiki` | 知识库搜索/管理 | `feishu wiki search-nodes --query "weekly"` |
| `calendar` | 日历/日程管理 | `feishu calendar list-calendars --format json` |
| `contact` | 通讯录查询 | `feishu contact user get --user-id ou_xxx --format json` |
| `search` | 搜索应用/消息/文档 | `feishu search doc-wiki --query "report" --auth-mode user --format json` |
| `sheets` | 电子表格操作 | `feishu sheets ...` |
| `task` | 任务管理 | `feishu task ...` |
| `webhook` | Webhook 解析/验签/服务 | `feishu webhook serve --port 8000` |
| `ws` | WebSocket 连接 | `feishu ws run --print-payload` |
| `server` | 托管机器人服务 | `feishu server run` |

详细 CLI 命令参考见 [references/cli.md](references/cli.md)。

### 常用场景速查

**发消息：**
```bash
feishu im send-text --receive-id ou_xxx --text "hello"
feishu im send-markdown --receive-id ou_xxx --markdown-file report.md --format json
cat report.md | feishu im send-markdown --receive-id ou_xxx --markdown-stdin --format json
```

**多维表格：**
```bash
feishu bitable create-from-csv data.csv --app-name "Sales" --table-name "Q1"
feishu bitable list-records --app-token app_xxx --table-id tbl_xxx --all --format json
feishu bitable create-record --app-token app_xxx --table-id tbl_xxx --fields-json '{"Name":"Alice","Score":95}'
```

**云文档：**
```bash
feishu docx create --title "Weekly Report" --format json
feishu docx insert-content --document-id doccn_xxx --content-file report.md --content-type markdown --document-revision-id -1 --format json
feishu docx get-content --doc-token doccn_xxx --doc-type docx --content-type markdown --output ./report.md
```

**知识库：**
```bash
feishu wiki search-nodes --query "project plan" --all --format json
feishu wiki list-spaces --all --format json
```

**日历：**
```bash
feishu calendar list-calendars --page-size 50 --format json
feishu calendar create-event --calendar-id cal_xxx --event-file ./event.json --format json
feishu calendar attach-material --calendar-id cal_xxx --event-id evt_xxx --path ./agenda.md --format json
```

**搜索（需要 user auth）：**
```bash
feishu search doc-wiki --query "weekly report" --auth-mode user --format json
feishu search message --query "incident" --chat-type group_chat --auth-mode user --format json
```

**通讯录：**
```bash
feishu contact user get --user-id ou_xxx --user-id-type open_id --format json
feishu contact department search --query "engineering" --format json
```

**云盘/权限：**
```bash
feishu drive upload-file report.pdf --parent-type explorer --parent-node fld_xxx
feishu drive grant-edit --token doccn_xxx --resource-type docx --member-id ou_xxx --permission edit --format json
```

## Python SDK 速查

```python
from feishu_bot_sdk import FeishuClient, FeishuConfig, MessageService

config = FeishuConfig(app_id="cli_xxx", app_secret="xxx")
client = FeishuClient(config)
msg = MessageService(client)
msg.send_text(receive_id_type="open_id", receive_id="ou_xxx", text="hello")
```

### 可用服务

| 服务 | 用途 |
|------|------|
| `MessageService` | 消息发送/回复/编辑/撤回/反应/置顶 |
| `CardKitService` | CardKit 卡片实体创建/流式更新/配置 |
| `MediaService` | 图片/文件上传下载 |
| `BitableService` | 多维表格应用/表/记录 CRUD |
| `DocxService` | 云文档创建、Markdown 写入 |
| `DriveFileService` | 文件上传、导入导出任务 |
| `DrivePermissionService` | 文件权限管理 |
| `WikiService` | 知识库空间/节点搜索管理 |
| `DocContentService` | 文档内容导出为 Markdown |
| `CalendarService` | 日历/日程 CRUD、忙闲查询 |
| `ContactService` | 用户/部门查询 |
| `SearchService` | 应用/消息/文档搜索 |
| `SheetsService` | 电子表格操作 |
| `TaskService` | 任务管理 |
| `BotService` | 机器人信息 |

所有服务都有 `Async*` 异步版本（如 `AsyncMessageService`）。

详细 SDK API 参考见 [references/sdk.md](references/sdk.md)。

## 事件处理

Webhook、WebSocket、FeishuBotServer 模式详见 [references/events.md](references/events.md)。

```python
from feishu_bot_sdk import FeishuBotServer

server = FeishuBotServer(app_id="cli_xxx", app_secret="xxx")

@server.on_im_message_receive
def handle_message(event):
    print(f"{event.sender_open_id}: {event.text}")

server.run()
```

## Agent 使用提示

- 分页查询优先用 `--all`：`bitable list-records`、`wiki list-spaces`、`wiki search-nodes`、`docx list-blocks`
- 文档写入优先用 `docx insert-content --content-type markdown`，避免手动构建 block
- 日历附件用 `calendar attach-material`，避免权限问题
- 搜索类命令（`search app/message/doc-wiki`）需要 `--auth-mode user`
- `bitable list-records` 支持 `--view-id`、`--filter`、`--sort`、`--field-names`
- 权限相关参数使用严格选项：`--member-id-type`、`--resource-type`、`--permission`

## 关键约定

- **receive_id_type**: `open_id`（默认）、`user_id`、`union_id`、`chat_id`
- **member_id_type**: `open_id`、`user_id`、`union_id`
- **msg_type**: `text`、`post`、`image`、`interactive`、`file`、`audio`、`media`、`share_chat`、`share_user`、`sticker`
- **异常体系**: `SDKError` > `ConfigurationError`、`HTTPRequestError`、`FeishuError`
- **速率限制**: 默认开启，自适应 QPS 调节
