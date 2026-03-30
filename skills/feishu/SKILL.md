---
name: feishu
description: >
  飞书（Lark）开放平台 CLI 和 Python SDK 使用指南。
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

# feishu CLI

飞书开放平台 CLI。提供 `feishu` 命令行工具，同时也是 Python SDK（同步/异步）。

## Agent 使用守则

- 只要任务涉及飞书 API 或 `feishu` CLI，先激活 `feishu` skill，再执行命令。
- 不要凭记忆猜测 CLI 命令名、参数名、认证行为。优先以本 skill、`references/cli.md` 或 `feishu <command> --help` 为准。
- 不要打印、回显或记录 token / secret / 敏感环境变量原值。
- 优先使用环境变量或宿主注入的认证。除非做底层认证调试，不要手工传 `--user-access-token`、`--user-refresh-token`、`--access-token`、`--app-secret`。
- 当用户要求"以我身份上传""归我所有""放到我的空间"时：
  - 不要复用旧任务记忆里的 folder token / parent node
  - 先用 `feishu auth whoami --format json` 确认当前用户身份
  - 对 requester-owned 上传优先用 `feishu drive +requester-upload`
  - 做最终 owner 校验：`feishu drive meta --check-requester-owner --as user --format json`

---

## 命令体系：三层模型

CLI 按用途分为三层，从高到低：

### Layer 1: Shortcut（+前缀）— 高层工作流

把多个 API 调用封装成一步操作，面向人类和 Agent 最友好的入口。命名带 `+` 前缀。

```bash
feishu bitable +create-from-csv data.csv --app-name "Sales" --table-name "Q1" --format json
feishu docx +insert-content --document-id doccn_xxx --content-file report.md --format json
feishu calendar +attach-material --calendar-id cal_xxx --event-id evt_xxx ./agenda.md --format json
feishu drive +requester-upload ./report.pdf --as user --format json
feishu mail +send-markdown --user-mailbox-id me --to-email user@example.com --subject "日报" --markdown-file ./report.md --format json
feishu docx +convert-content --content-file draft.md --content-type markdown --format json
```

### Layer 2: Service Command — 元数据驱动的平台接口映射

按 `<service> <resource> <method>` 结构自动生成，参数统一走 `--params` / `--data`：

```bash
feishu drive files list --params '{"folder_token":"fld_xxx"}' --format json
feishu calendar events list --params '{"calendar_id":"primary"}' --format json
feishu im messages list --params '{"container_id":"oc_xxx","container_id_type":"chat"}' --format json
feishu task tasks list --format json
```

**不确定接口怎么调？先查 schema：**

```bash
feishu schema list                        # 列出所有 service
feishu schema list drive                  # 列出 drive 下的 resource/method
feishu schema show drive.files.list       # 查看参数、scopes、文档链接
```

### Layer 3: Raw API — 兜底调试

直接调用任意 OpenAPI 路径：

```bash
feishu api GET /open-apis/drive/v1/files --params '{"folder_token":"fld_xxx"}' --format json
feishu api POST /open-apis/im/v1/messages --params '{"receive_id_type":"open_id"}' --data '{"receive_id":"ou_xxx","msg_type":"text","content":"{\"text\":\"hello\"}"}' --as bot --format json
```

### 优先级选择

1. 有 shortcut 时用 shortcut（最简洁）
2. 没有 shortcut 时用 service command（`feishu schema show` 查看用法）
3. 都不覆盖时用 `feishu api`（全覆盖兜底）

---

## 身份模型：`--as`

所有命令通过 `--as` 指定身份：

| 值 | 含义 |
|---|---|
| `--as bot` | 使用 app/tenant token（默认） |
| `--as user` | 使用用户 OAuth token |
| `--as auto` | 根据命令元数据和登录状态自动选择 |

```bash
feishu drive files list --params '{"folder_token":"fld_xxx"}' --as user --format json
feishu im messages list --params '{"container_id":"oc_xxx","container_id_type":"chat"}' --as bot --format json
```

**决策优先级**：显式 `--as` > 命令元数据 > profile `default_as` > 当前登录状态。

---

## 诊断：auth + doctor

### 查看当前认证状态

```bash
feishu auth status --format json              # 当前身份、token 状态、scopes
feishu auth status --verify --format json      # 额外做服务端校验
```

### 检查 scope 是否满足

```bash
feishu auth check --scope "drive:file:upload docs:doc" --format json
```

### 环境健康检查

```bash
feishu doctor --format json                    # 检查 config、metadata、token、网络
feishu doctor --offline --format json           # 跳过网络检查
```

### 登录

```bash
feishu auth login --scope "offline_access contact:user:search" --format json
feishu auth login --recommend --domain calendar drive --format json
```

---

## 输出控制

### 格式

`--format json|pretty|table|csv|ndjson`（默认 `json`）

### 大输出控制（Agent 核心能力）

常规命令 stdout 默认上限 25000 字符。当输出过大时：

```bash
# 返回中会出现 _cli_output.truncated=true，看 hints 字段

# 方法 1：分片查看
feishu ... --output-offset 25000

# 方法 2：完整 JSON 写盘
feishu ... --save-output ./full.json

# 方法 3：关闭裁剪
feishu ... --full-output
```

### 分页

service command 支持自动分页：

```bash
feishu calendar events list --params '{"calendar_id":"primary"}' --page-all --format json
feishu calendar events list --params '{"calendar_id":"primary"}' --page-all --page-limit 50 --format json
feishu calendar events list --params '{"calendar_id":"primary"}' --page-size 20 --format json
```

### --dry-run

所有 service command 和 shortcut 支持 `--dry-run`，预览将要执行的 API 调用：

```bash
feishu drive +requester-upload ./file.pdf --dry-run --format json
```

---

## 环境变量配置

CLI 认证优先级：环境变量 > CLI 参数 > CLI profile > 本地 token store。

```bash
# 核心凭证（必需）
export FEISHU_APP_ID="cli_xxx"
export FEISHU_APP_SECRET="xxx"

# 默认身份（可选）
export FEISHU_DEFAULT_AS="auto"           # user / bot / auto

# 用户认证 token（--as user 或 auto 时可用）
export FEISHU_USER_ACCESS_TOKEN="u-xxx"
export FEISHU_USER_REFRESH_TOKEN="ur-xxx"

# 静态 token（可选）
export FEISHU_ACCESS_TOKEN="t-xxx"

# Token 存储配置
export FEISHU_PROFILE="default"
export FEISHU_NO_STORE="1"                # 禁用本地 token 存储
```

---

## 常用场景速查

### 发消息

```bash
feishu im send-text --receive-id ou_xxx --text "hello" --format json
feishu im send-markdown --receive-id ou_xxx --markdown-file report.md --format json
cat report.md | feishu im send-markdown --receive-id ou_xxx --markdown-stdin --format json
```

### 多维表格

```bash
feishu bitable +create-from-csv data.csv --app-name "Sales" --table-name "Q1" --format json
feishu bitable app_table_record records list --params '{"app_token":"app_xxx","table_id":"tbl_xxx"}' --page-all --format json
```

### 云文档

```bash
feishu docx +insert-content --document-id doccn_xxx --content-file report.md --format json
feishu docx get-content --doc-token doccn_xxx --doc-type docx --content-type markdown --output ./report.md
```

### 云盘

```bash
feishu drive +requester-upload ./report.pdf --as user --format json
feishu drive files list --params '{"folder_token":"fld_xxx"}' --as user --format json
```

### 日历

```bash
feishu calendar +attach-material --calendar-id cal_xxx --event-id evt_xxx ./agenda.md --format json
feishu calendar events list --params '{"calendar_id":"primary"}' --page-all --as user --format json
```

### 搜索

```bash
feishu search doc-wiki --query "weekly report" --as auto --format json
feishu search message --query "incident" --as auto --format json
```

### 邮件

```bash
feishu mail +send-markdown --user-mailbox-id me --to-email user@example.com --subject "日报" --markdown-file ./report.md --format json
```

### 通讯录

```bash
feishu auth whoami --format json
feishu contact user get --user-id ou_xxx --user-id-type open_id --format json
feishu contact user search --query "Alice" --as user --format json
```

### 权限

```bash
feishu drive grant-edit --token doccn_xxx --resource-type docx --member-id ou_xxx --permission edit --format json
```

---

## 安装

```bash
pip install feishu-bot-sdk
# 或作为全局 CLI：
uv tool install feishu-bot-sdk
```

---

## Python SDK 速查

```python
from feishu_bot_sdk import FeishuClient, FeishuConfig, MessageService

config = FeishuConfig(app_id="cli_xxx", app_secret="xxx")
client = FeishuClient(config)
msg = MessageService(client)
msg.send_text(receive_id_type="open_id", receive_id="ou_xxx", text="hello")
```

所有服务都有 `Async*` 异步版本。详细 SDK API 见 [references/sdk.md](references/sdk.md)。

---

## 事件处理

```python
from feishu_bot_sdk import FeishuBotServer

server = FeishuBotServer(app_id="cli_xxx", app_secret="xxx")

@server.on_im_message_receive
def handle_message(event):
    print(f"{event.sender_open_id}: {event.text}")

server.run()
```

详见 [references/events.md](references/events.md)。

---

## 关键约定

- **receive_id_type**: `open_id`（默认）、`user_id`、`union_id`、`chat_id`
- **member_id_type**: `open_id`、`user_id`、`union_id`
- **异常体系**: `SDKError` > `ConfigurationError`、`HTTPRequestError`、`FeishuError`
- **错误输出**（`--format json` 时）：`{"ok": false, "error": {"type": "...", "code": ..., "message": "...", "hint": "...", "retryable": false}, "exit_code": N}`

---

## 详细参考

- [references/cli.md](references/cli.md) — CLI 命令完整参考
- [references/sdk.md](references/sdk.md) — Python SDK API 参考
- [references/events.md](references/events.md) — 事件处理（Webhook / WebSocket / Server）
- [references/mail.md](references/mail.md) — 邮箱功能专项参考
