# CLI Command Reference

## 命令体系概览

```
feishu
├── config          # 配置管理
├── auth            # 认证/身份
├── doctor          # 环境诊断
├── schema          # 查看 API schema
├── api             # Raw API 调用
├── completion      # Shell 自动补全
├── webhook         # Webhook 工具命令
├── ws              # WebSocket 长连接
├── server          # 托管服务
├── media           # 上传/下载 IM 媒体
├── <service>       # 元数据驱动的 service commands
│   ├── <resource> <method>    # Layer 2: service command
│   └── +<shortcut>            # Layer 1: 高层工作流
├── bitable         # 多维表格（shortcuts + service commands）
└── docx            # 云文档（shortcuts）
```

---

## Global Flags

所有命令共享的参数：

```
--format json|pretty|table|csv|ndjson|human   输出格式（默认 json）
--as user|bot|auto                            身份（默认 bot）
--app-id TEXT                                 App ID (env: FEISHU_APP_ID)
--app-secret TEXT                             App Secret (env: FEISHU_APP_SECRET)
--profile TEXT                                CLI profile 名称
--base-url URL                                API 地址 (默认: https://open.feishu.cn/open-apis)
--timeout SECONDS                             HTTP 超时
--max-output-chars INT                        stdout 上限 (默认: 25000)
--output-offset INT                           查看后续 JSON 片段
--save-output PATH                            完整 JSON 写盘
--full-output                                 禁用 stdout 裁剪
--no-store                                    禁用本地 token 存储
```

Service command / api / shortcut 额外支持：

```
--params JSON                                 查询/路径参数
--data JSON                                   请求体
--page-all                                    自动分页
--page-size INT                               每页条数
--page-limit INT                              最大页数 (默认: 10)
--page-delay INT                              页间延迟 ms (默认: 200)
--output PATH                                 业务输出写文件（如下载）
--dry-run                                     预览将执行的 API 调用
```

---

## config — 配置管理

```bash
# 初始化 profile
printf 'your_app_secret' | feishu config init --profile default --app-id cli_xxx --app-secret-stdin --default-as auto --set-default --format json

# 查看当前 profile
feishu config show --format json

# 列出所有 profiles
feishu config list-profiles --format json

# 设置默认 profile
feishu config set-default-profile my-profile

# 设置默认身份
feishu config set-default-as --as user

# 删除 profile
feishu config remove-profile old-profile

# 从旧 token store 迁移
feishu config migrate-token-store --source-path /path/to/old/tokens.json
```

---

## auth — 认证/身份

```bash
# 获取当前 token
feishu auth token --format json
feishu auth token --as bot --format json

# 查看当前登录用户
feishu auth whoami --format json

# 查看完整认证状态
feishu auth status --format json
feishu auth status --verify --format json         # 额外服务端校验

# 检查 scope 是否满足
feishu auth check --scope "drive:file:upload" --scope "docs:doc" --format json
feishu auth check --scope "drive:file:upload docs:doc" --format json

# 列出可用 scopes
feishu auth scopes --format json
feishu auth scopes --domain calendar drive --recommend --format json

# 列出所有已配置的 profiles
feishu auth list --format json

# 登录（OAuth，默认 device flow）
feishu auth login --scope "offline_access contact:user:search" --format json
feishu auth login --recommend --domain calendar drive --format json
feishu auth login --device-code --format json
feishu auth login --localhost --no-browser --format json

# 刷新 token
feishu auth refresh --format json

# 登出
feishu auth logout --format json
feishu auth logout --all-profiles --format json
```

---

## doctor — 环境诊断

```bash
feishu doctor --format json                # 检查 config、metadata、token、网络
feishu doctor --offline --format json       # 跳过网络检查
```

检查项：config、metadata、identity.user、identity.bot、token_store、open_api endpoint、accounts endpoint。

---

## schema — 查看 API 元数据

**不确定某个 API 怎么调时，先查 schema。**

```bash
# 列出所有 service
feishu schema list --format json

# 列出某个 service 的 resource / method
feishu schema list drive --format json

# 查看具体 method 的参数、scopes、文档链接
feishu schema show drive.files.list --format json
feishu schema show calendar.events.create --format json

# 查看 shortcut schema
feishu schema show bitable.+create-from-csv --format json

# 列出所有 schema path
feishu schema paths --format json
```

---

## api — Raw API 调用

```bash
feishu api GET /open-apis/drive/v1/files --params '{"folder_token":"fld_xxx"}' --format json
feishu api POST /open-apis/im/v1/messages --params '{"receive_id_type":"open_id"}' \
  --data '{"receive_id":"ou_xxx","msg_type":"text","content":"{\"text\":\"hello\"}"}' --as bot --format json
feishu api GET /authen/v1/user_info --as user --format json

# 预览
feishu api GET /open-apis/drive/v1/files --params '{"folder_token":"fld_xxx"}' --dry-run --format json
```

---

## completion — Shell 自动补全

```bash
feishu completion bash
feishu completion zsh
feishu completion fish
```

---

## Shortcuts（+前缀命令）

### bitable +create-from-csv

从 CSV 创建多维表格：

```bash
feishu bitable +create-from-csv data.csv --app-name "Sales" --table-name "Q1" --format json
feishu bitable +create-from-csv data.csv --app-name "Sales" --table-name "Q1" --grant-member-id ou_xxx --format json
feishu bitable +create-from-csv data.csv --app-name "Sales" --table-name "Q1" --dry-run --format json
```

### docx create

创建原生飞书 Docx 云文档：

```bash
feishu docx create --title "日报" --folder-token fld_xxx --format json
feishu docx create --title "日报" --as user --format json
```

说明：

- `docx create` 是常规命令，不是 `+shortcut`
- 它可能不会出现在 `feishu schema list docx` 的 shortcuts 列表里；需要创建文档时优先看 `feishu docx --help`

### docx +insert-content

将 Markdown/HTML 内容插入云文档：

```bash
feishu docx +insert-content --document-id doccn_xxx --content-file report.md --format json
feishu docx +insert-content --document-id doccn_xxx --content "# Title\n\nBody" --content-type markdown --format json
cat report.md | feishu docx +insert-content --document-id doccn_xxx --content-stdin --format json
# 默认返回精简摘要，排查时加 --full-response
feishu docx +insert-content --document-id doccn_xxx --content-file report.md --full-response --format json
```

说明：

- `--content-file` 模式下，Markdown 中的相对本地图片路径按该文件所在目录解析
- 如果 `docx create` 已成功但 `+insert-content` 失败，应保留原 `doc_id` 并报告部分成功，不要重复创建新文档

### docx +convert-content

将 Markdown/HTML 转换为飞书 Docx 块：

```bash
feishu docx +convert-content --content-file draft.md --content-type markdown --format json
feishu docx +convert-content --content "# Hello" --output ./blocks.json --format json
```

### calendar +attach-material

上传文件并附加到日历事件：

```bash
feishu calendar +attach-material --calendar-id cal_xxx --event-id evt_xxx ./agenda.md --format json
```

### drive +requester-upload

以当前用户身份上传文件到用户空间（自动创建子目录 + 校验 owner）：

```bash
feishu drive +requester-upload ./report.pdf --as user --format json
feishu drive +requester-upload ./report.pdf --folder-name "Uploads" --format json
```

### mail +send-markdown

渲染 Markdown 为 HTML 邮件并发送（自动处理图片内联）：

```bash
feishu mail +send-markdown --user-mailbox-id me --to-email user@example.com --subject "日报" --markdown-file ./report.md --format json
feishu mail +send-markdown --user-mailbox-id me --to-email a@example.com --to-email b@example.com --cc-email cc@example.com --subject "周报" --markdown "# 周报\n\n完成情况..." --format json
```

---

## Service Commands（元数据驱动）

Service commands 按 `<service> <resource> <method>` 结构组织，参数走 `--params` / `--data`。

### 可用 services

当前已同步的 service: `calendar`, `drive`, `im`, `mail`, `minutes`, `sheets`, `task`, `vc`, `wiki`。

用 `feishu schema list` 查看实时列表。

### 示例

```bash
# Drive
feishu drive files list --params '{"folder_token":"fld_xxx"}' --as user --format json
feishu drive files copy --params '{"file_token":"doc_xxx"}' --data '{"folder_token":"fld_xxx","name":"copy","type":"file"}' --format json

# Calendar
feishu calendar events list --params '{"calendar_id":"primary"}' --page-all --as user --format json
feishu calendar events create --params '{"calendar_id":"primary"}' --data '{"summary":"Meeting","start_time":{"timestamp":"1700000000"},"end_time":{"timestamp":"1700003600"}}' --format json
feishu calendar calendars search --data '{"query":"weekly sync"}' --format json

# IM
feishu im messages list --params '{"container_id":"oc_xxx","container_id_type":"chat"}' --page-all --format json

# Task
feishu task tasks list --format json
feishu task tasks create --data '{"summary":"Review PR","due":{"timestamp":"1700086400"}}' --format json

# Wiki
feishu wiki spaces list --page-all --format json

# Mail
feishu mail mailboxes messages list --params '{"user_mailbox_id":"me","folder_id":"INBOX"}' --page-all --format json
```

---

## Click 命令：webhook / ws / server / media

### media -- 上传下载

```bash
feishu media upload-image photo.png --format json
feishu media upload-file document.pdf --file-type pdf --format json
feishu media download-file img_v3_xxx ./output.jpg --message-id om_xxx --resource-type image --as bot --format json
```

### webhook

```bash
feishu webhook decode --body-json '{"encrypt":"..."}' --encrypt-key KEY
feishu webhook verify-signature --headers-json '{"X-Lark-Signature":"..."}' --body-json '{"..."}' --encrypt-key KEY
feishu webhook parse --body-json '{"..."}' --encrypt-key KEY
feishu webhook serve --host 0.0.0.0 --port 8000 --path /webhook/feishu --print-payload
```

### ws -- WebSocket

```bash
feishu ws endpoint --format json
feishu ws run --print-payload
feishu ws run --event-type im.message.receive_v1 --max-events 10
```

### server -- 托管服务

```bash
feishu server run --print-payload
feishu server start --pid-file /tmp/feishu.pid --log-file /tmp/feishu.log
feishu server status --pid-file /tmp/feishu.pid --format json
feishu server stop --pid-file /tmp/feishu.pid
```

---

## 大输出控制

```bash
# 先落盘再分析
feishu search app --query "calendar" --save-output ./search-full.json --format json

# 查看后续 JSON 片段（_cli_output.next_output_offset 指示）
feishu search app --query "calendar" --output-offset 25000 --format json

# 关闭裁剪
feishu search app --query "calendar" --full-output --format json
```

Agent 规则：
- service command 优先用 `--page-size` / `--page-all` 控制数据量
- 不支持翻页的大结果（如 `calendar list-freebusy`）用 `--save-output`

---

## Stdin 输入模式

所有支持 `--*-json` 的命令同时支持 `--*-file PATH` 和 `--*-stdin`：

```bash
generate_report | feishu im send-markdown --receive-id ou_xxx --markdown-stdin --format json
echo '{"text":"hello"}' | feishu im send --receive-id ou_xxx --msg-type text --content-stdin
feishu im send --receive-id ou_xxx --msg-type interactive --content-file card.json
```

---

## 错误输出格式

`--format json` 时错误返回结构化 envelope：

```json
{
  "ok": false,
  "error": {
    "type": "http_error",
    "code": 99991679,
    "message": "...",
    "hint": "missing user scopes: contact:user:search; re-login with: feishu auth login --scope ...",
    "retryable": false,
    "status_code": 400,
    "response_excerpt": "..."
  },
  "exit_code": 4
}
```

Exit codes: 0=成功, 1=内部错误, 2=参数/配置错误, 3=飞书API错误, 4=HTTP错误。
