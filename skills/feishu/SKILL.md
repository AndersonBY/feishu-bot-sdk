---
name: feishu
description: >
  飞书（Lark）开放平台 Python SDK 和 CLI 工具使用指南。
  当用户需要处理任何飞书相关任务时触发此 skill，包括但不限于：
  (1) 飞书消息发送（文本、Markdown、图片、卡片），
  (2) 飞书 CardKit 卡片实体（创建、流式更新、streaming_mode、回调响应），
  (3) 飞书云文档操作（创建、编辑、导出文档内容），
  (4) 飞书多维表格/Bitable（创建表格、CSV导入、记录增删改查），
  (5) 飞书云盘/Drive（文件上传下载、权限管理），
  (6) 飞书知识库/Wiki（搜索、空间管理），
  (7) 飞书日历/Calendar（日程创建、查询、附件），
  (8) 飞书邮箱/Mail（用户邮箱、邮件组、公共邮箱、Markdown邮件发送），
  (9) 飞书通讯录/Contact（用户、部门查询），
  (10) 飞书搜索（应用、消息、文档搜索），
  (11) 飞书机器人开发（Webhook、WebSocket 事件处理），
  (12) 任何涉及 `feishu` CLI 命令或 `feishu_bot_sdk` Python 导入的任务。
  即使用户没有明确提到 feishu-bot-sdk，只要任务涉及飞书平台的 API 操作、
  飞书文档处理、飞书数据管理、飞书自动化，都应使用此 skill。
---

# feishu-bot-sdk

飞书开放平台 Python SDK + CLI。提供 `feishu` 命令行工具和 Python 同步/异步 API。

## Agent 使用守则

- 在任何支持 skill 激活的 Agent 环境里，只要任务涉及飞书 API、`feishu` CLI 或 `feishu_bot_sdk`，先激活 `feishu` skill，再执行命令。
- 不要凭记忆猜测 CLI 命令名、参数名、认证行为。优先以本 skill、`references/cli.md` 或 `feishu ... --help` 为准；旧 transcript 里的参数可能已经过期。
- 优先使用环境变量或宿主管理的认证注入。除非是在做显式的底层认证调试，不要手工传 `--user-access-token`、`--user-refresh-token`、`--access-token`、`--app-secret`。
- 不要打印、回显、转述或记录 token / secret / 敏感环境变量原值。
- 当用户明确要求“以我身份上传”“归我所有”“放到我的空间”时，不要复用旧任务记忆里的 folder token / parent node。先解析当前用户身份和目标位置，再用实时 Drive 元数据校验 owner / permission。
- 对 `drive/*` 和“创建后要求 owner/creator 是当前用户本人”的任务，不要用 `--auth-mode auto` 冒充用户身份。`auto` 对很多非 user-centric endpoint 会优先走 tenant。先执行 `feishu auth whoami --auth-mode user --format json`；只有成功后才用 `--auth-mode user`，失败就停止并说明当前 requester token 不可用。
- `feishu auth whoami --auth-mode user` 成功只说明“当前 user token 可用”，不等于“创建出来的资源 owner 一定是当前用户本人”。普通 `feishu drive upload-file` 在 user 模式下仍可能生成应用主体名下文件。
- 对 requester-owned 的 Drive 上传，优先先拿当前 requester 的 root folder：`feishu drive root-folder-meta --auth-mode user --format json`。必要时先 `feishu drive create-folder --auth-mode user --folder-token <root_token> --name <folder>`，再把文件上传到这个新目录。不要直接把历史 transcript 里的 `parent_node` 当成“我的空间”。
- owner-sensitive 任务必须做最终校验。优先使用 `feishu drive meta --check-requester-owner --auth-mode user --format json`，或 `feishu drive upload-file --check-requester-owner ... --auth-mode user --format json`。只有 `_cli_diagnostics.requester_owner_verified=true`，或者 `owner_id` 明确等于当前用户的 `open_id/user_id/union_id`，才能宣称“归用户本人所有”。
- 如果实时校验里 `owner_id` / `latest_modify_user` 与当前用户 ID 不一致，就明确告诉用户“这次资源不是用户本人 owner”，不要因为命令走了 user mode 就改写结论。

## 环境变量配置（优先级最高）

CLI 认证优先级：环境变量 > CLI 参数 > 本地 token store。

使用前先确认环境变量是否已设置，如果已设置则无需传递 `--app-id` / `--app-secret` 等参数：

```bash
# 核心凭证（必需）
export FEISHU_APP_ID="cli_xxx"
export FEISHU_APP_SECRET="xxx"

# 认证模式（可选，默认 tenant）
export FEISHU_AUTH_MODE="tenant"        # tenant / user / auto

# 静态 token（可选，跳过自动认证）
export FEISHU_ACCESS_TOKEN="t-xxx"

# 用户认证 token（auth_mode=user 或 auto 时可用）
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

处理“给我权限 / 分享给我 / 把我加入”这类请求时，默认把“我”理解为当前操作者。
优先用 `feishu auth whoami --auth-mode user --format json` 解析当前登录用户，再执行权限变更。

当同时具备 tenant 凭证和 user token 时，优先使用 `FEISHU_AUTH_MODE=auto`：
- 搜索、日历、任务、邮箱、`auth whoami` 这类明显偏用户身份的 API 会优先走 user token
- 如果 endpoint 明确不支持 user token，CLI 会自动回退到 tenant
- 只有在你要强制指定身份时，才显式传 `--auth-mode tenant` 或 `--auth-mode user`

## 安装

```bash
pip install feishu-bot-sdk
# 或作为全局 CLI 工具：
uv tool install feishu-bot-sdk
```

## CLI 命令速查

全局参数：`--format human|json`、`--app-id`、`--app-secret`、`--auth-mode tenant|user|auto`、`--base-url`、`--timeout`、
`--max-output-chars`、`--output-offset`、`--save-output`、`--full-output`

所有命令支持 `--format json` 输出机器可读格式，支持 stdin 输入（`--*-stdin`、`--*-file`、`--*-json`）。
常规命令默认把 stdout 控制在 25000 字符内；当输出过大时，CLI 会返回 `_cli_output`，告诉你如何查看后续 JSON 片段或下一页。

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
| `mail` | 邮箱/邮件组/公共邮箱 | `feishu mail message send-markdown --user-mailbox-id me --to-email user@example.com --subject "日报" --markdown-file ./report.md` |
| `contact` | 通讯录查询 | `feishu contact user get --user-id ou_xxx --format json` |
| `search` | 搜索应用/消息/文档 | `feishu search doc-wiki --query "report" --auth-mode auto --format json` |
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
feishu bitable list-tables --app-token app_xxx --format json
feishu bitable list-records --app-token app_xxx --table-id tbl_xxx --all --format json
feishu bitable list-views --app-token app_xxx --format json
feishu bitable create-record --app-token app_xxx --fields-json '{"Name":"Alice","Score":95}'
```

**云文档：**
```bash
feishu docx create --title "Weekly Report" --format json
feishu docx insert-content --document-id doccn_xxx --content-file report.md --content-type markdown --document-revision-id -1 --format json
# 默认返回精简摘要；只有调试转换/插入细节时才加 --full-response
feishu docx get-content --doc-token doccn_xxx --doc-type docx --content-type markdown --output ./report.md
```

**知识库：**
```bash
feishu wiki search-nodes --query "project plan" --all --format json
feishu wiki list-spaces --all --format json
```

**日历：**
```bash
feishu calendar list-calendars --all --format json
feishu calendar create-event --calendar-id cal_xxx --event-file ./event.json --format json
feishu calendar attach-material --calendar-id cal_xxx --event-id evt_xxx --path ./agenda.md --format json
```

**搜索（通常直接用 auto）：**
```bash
feishu search doc-wiki --query "weekly report" --auth-mode auto --format json
feishu search message --query "incident" --chat-type group_chat --auth-mode auto --format json
```

**通讯录：**
```bash
feishu auth whoami --auth-mode user --format json
feishu contact user get --user-id ou_xxx --user-id-type open_id --format json
feishu contact department search --query "engineering" --format json
```

**云盘/权限：**
```bash
feishu drive root-folder-meta --auth-mode user --format json
feishu drive create-folder --auth-mode user --folder-token fld_root_xxx --name "Uploads" --format json
feishu drive upload-file report.pdf --parent-type explorer --parent-node fld_xxx
feishu drive upload-file report.pdf --parent-type explorer --parent-node fld_xxx --auth-mode user --check-requester-owner --format json
feishu drive meta --request-docs-json '[{"doc_token":"file_xxx","doc_type":"file"}]' --auth-mode user --check-requester-owner --format json
feishu drive grant-edit --token doccn_xxx --resource-type docx --member-id ou_xxx --permission edit --format json
feishu drive grant-edit --token doccn_xxx --resource-type docx --member-id me --permission edit --auth-mode auto --format json
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
| `MailMailboxService` | 用户邮箱别名、回收站管理 |
| `MailMessageService` | 邮件发送/查询/Markdown 渲染 |
| `MailFolderService` | 邮箱文件夹管理 |
| `MailContactService` | 邮箱联系人管理 |
| `MailRuleService` | 收信规则管理 |
| `MailEventService` | 邮箱事件订阅 |
| `MailAddressService` | 邮箱地址状态查询 |
| `MailGroupService` | 邮件组管理 |
| `MailGroupAliasService` | 邮件组别名管理 |
| `MailGroupMemberService` | 邮件组成员管理 |
| `MailGroupPermissionMemberService` | 邮件组权限成员管理 |
| `MailGroupManagerService` | 邮件组管理员管理 |
| `PublicMailboxService` | 公共邮箱管理 |
| `PublicMailboxAliasService` | 公共邮箱别名管理 |
| `PublicMailboxMemberService` | 公共邮箱成员管理 |
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

- 机器调用统一加 `--format json`
- 常规命令 stdout 默认上限 25000 字符；如果返回里出现 `_cli_output.truncated=true`：
  - 先看 `_cli_output.hints`
  - 用 `--output-offset <next_output_offset>` 看后续 JSON 片段
  - 或用 `--save-output ./full.json` 把完整标准化 JSON 写盘
- 对支持翻页的命令，优先用 `--page-size` + `--page-token` 做增量抓取；只有在确认总量可控时才用 `--all`
- 已支持 `--all` 的高频查询包括：`bitable list-records`、`wiki list-spaces`、`wiki search-nodes`、`docx list-blocks`、`mail message list`、`mail group list`、`mail group member list`、`calendar list-calendars`、`calendar search-calendars`、`calendar list-events`、`calendar search-events`、`contact user by-department`、`contact user search`、`contact department children`、`contact department parent`、`contact department search`、`contact scope get`
- `bitable list-tables` 也支持 `--all`
- 对目前没有 CLI 翻页参数的命令，避免直接把大结果塞进上下文：`drive list-members`、`calendar list-freebusy`、`calendar batch-freebusy`
- 文档写入优先用 `docx insert-content --content-type markdown`，避免手动构建 block
- `docx insert-content` 默认只返回精简摘要；只有在排查 block 转换/图片替换时才加 `--full-response`
- 日历附件用 `calendar attach-material`，避免权限问题
- 邮件发送优先用 `mail message send-markdown`，自动处理 Markdown 渲染和图片内联
- 搜索类命令（`search app/message/doc-wiki`）通常直接用 `--auth-mode auto`
- `bitable list-records` 支持 `--view-id`、`--filter`、`--sort`、`--field-names`
- Bitable 表级命令在应用有默认表或只有唯一一张表时，可省略 `--table-id`；若有多张表且默认表为空，先运行 `bitable list-tables`
- `bitable get-app` / `copy-app` 在能唯一确定表时，会补充 `data.table_id`
- 权限相关参数使用严格选项：`--member-id-type`、`--resource-type`、`--permission`
- 如果用户说“给我 / 分享给我 / 授权给我”，先用 `feishu auth whoami --auth-mode user --format json` 解析当前登录用户
- `drive/docx/bitable grant-edit` 支持 `--member-id me`，会按 `--member-id-type` 解析当前登录用户的 `open_id` / `user_id` / `union_id`
- 邮箱批量操作优先用 `--*-file` 或 `--*-stdin` 传递 JSON 数组

## 关键约定

- **receive_id_type**: `open_id`（默认）、`user_id`、`union_id`、`chat_id`
- **member_id_type**: `open_id`、`user_id`、`union_id`
- **msg_type**: `text`、`post`、`image`、`interactive`、`file`、`audio`、`media`、`share_chat`、`share_user`、`sticker`
- **异常体系**: `SDKError` > `ConfigurationError`、`HTTPRequestError`、`FeishuError`
- **速率限制**: 默认开启，自适应 QPS 调节

## 邮箱功能（Mail）

### CLI 命令示例

```bash
# 查询邮箱地址状态
feishu mail address query-status --email ops@example.com --email alerts@example.com --format json

# 列出收件箱邮件（自动翻页）
feishu mail message list --user-mailbox-id me --folder-id INBOX --all --format json

# 如果输出仍然太大，先落盘再分析
feishu mail message list --user-mailbox-id me --folder-id INBOX --all --save-output ./mail-full.json --format json

# 从 Markdown 文件渲染 HTML 邮件并发送
feishu mail message send-markdown --user-mailbox-id me --to-email user@example.com --subject "日报" --markdown-file ./report.md --format json

# 创建用户邮箱别名
feishu mail mailbox alias create --user-mailbox-id me --email-alias alias@example.com --format json

# 永久删除回收站中的用户邮箱，并转移邮件
feishu mail mailbox delete-from-recycle-bin --user-mailbox-id old@example.com --transfer-mailbox archive@example.com --format json

# 创建邮件组
feishu mail group create --mailgroup-json '{"email":"ops@example.com","name":"Ops Group"}' --format json

# 批量添加公共邮箱成员
feishu mail public-mailbox member batch-create --public-mailbox-id support@example.com --items-file ./members.json --format json
```

### SDK 使用示例

```python
from feishu_bot_sdk import (
    FeishuClient,
    FeishuConfig,
    MailAddressService,
    MailMessageService,
    MailGroupService,
    render_markdown_email,
)

client = FeishuClient(FeishuConfig(app_id="cli_xxx", app_secret="xxx"))

# 查询邮箱地址状态
address = MailAddressService(client)
status = address.query_status(["ops@example.com", "alerts@example.com"])
print(status.user_list)

# 列出收件箱邮件
message = MailMessageService(client)
for item in message.iter_messages("me", folder_id="INBOX", page_size=50):
    print(item.get("subject"))

# Markdown 邮件渲染（自动处理图片内联）
rendered = render_markdown_email(
    "# 日报\n\n![图表](./chart.png)\n\n![远程图](https://cdn.example.com/chart.png)",
    base_dir="."
)
print(rendered.html[:120], len(rendered.inline_images))

# 发送 Markdown 邮件
message.send_markdown(
    "me",
    subject="日报",
    to=["user@example.com"],
    markdown="# 日报\n\n任务已完成",
)

# 创建邮件组
group = MailGroupService(client)
created = group.create_mailgroup({"email": "ops@example.com", "name": "Ops Group"})
print(created.mailgroup_id)
```

### 邮箱功能要点

- **用户邮箱**：别名管理、邮件发送/查询、文件夹管理、联系人管理、收信规则、事件订阅
- **邮件组**：邮件组 CRUD、别名管理、成员管理、权限成员管理、管理员管理
- **公共邮箱**：公共邮箱 CRUD、别名管理、成员管理
- **Markdown 邮件**：`send-markdown` 自动渲染 HTML、处理本地/远程图片内联、生成纯文本版本
- **图片处理**：本地图片自动转 base64 内联，远程图片自动下载后内联，失败时保留原始 URL
- **批量操作**：成员批量添加/删除支持 `--*-file` 或 `--*-stdin` 传递 JSON 数组
- **分页查询**：`mail message list`、`mail group list`、`mail group member list` 等支持 `--all` 自动翻页
- **邮箱删除**：永久删除用户邮箱时可用 `--transfer-mailbox` 转移邮件；移除公共邮箱到回收站时可用 `--to-mail-address` 指定接收地址

详细 API 参考见 [references/mail.md](references/mail.md)。
