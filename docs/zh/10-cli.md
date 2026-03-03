# CLI 命令行工具

[English](../en/10-cli.md)

`feishu-bot-sdk` 提供 `feishu` 命令，适合脚本、CI 和 LLM Agent 直接调用。

## 安装

```bash
uv tool install feishu-bot-sdk
feishu --help
```

## 全局参数

- `--format human|json`：默认 `human`，机器调用建议 `json`
- `--app-id` / `--app-secret`：飞书应用凭证
- `--auth-mode tenant|user`：认证模式，默认 `tenant`
- `--access-token`：当前认证模式的静态 access token（可选）
- `--app-access-token`：OAuth code/refresh 交换使用（可选）
- `--user-access-token` / `--user-refresh-token`：用户态 token（`auth_mode=user` 常用）
- `--profile`：本地 token profile，默认读取 `FEISHU_PROFILE` 或 `default`
- `--token-store`：本地 token 存储路径
- `--no-store`：禁用本地 token 读写
- `--base-url`：默认 `https://open.feishu.cn/open-apis`
- `--timeout`：请求超时秒数

认证优先级：环境变量 > 命令行参数 > 本地 token store。

- 环境变量：`FEISHU_APP_ID` / `FEISHU_APP_SECRET` / `FEISHU_AUTH_MODE` / `FEISHU_ACCESS_TOKEN`
- 用户态环境变量：`FEISHU_USER_ACCESS_TOKEN` / `FEISHU_USER_REFRESH_TOKEN`
- OAuth 交换环境变量：`FEISHU_APP_ACCESS_TOKEN`
- Token store 变量：`FEISHU_PROFILE` / `FEISHU_TOKEN_STORE_PATH` / `FEISHU_NO_STORE`
- 兼容变量：`APP_ID` / `APP_SECRET`

## 常用命令

```bash
# 鉴权（推荐：无公网 localhost 回调）
feishu auth token --format json
feishu auth login --scope "offline_access contact:user.base:readonly" --no-browser --format json
feishu auth whoami --format json
feishu auth refresh --format json
feishu auth logout --format json

# 低层 OAuth 调试命令
feishu oauth authorize-url --redirect-uri https://example.com/callback --format json
feishu oauth exchange-code --code CODE --format json

# 发消息
feishu im send-text --receive-id ou_xxx --text "hello"
feishu im send-markdown --receive-id ou_xxx --markdown-file ./msg.md --format json
feishu im push-follow-up om_xxx --follow-ups-json '[{"content":"继续处理"}]' --format json
feishu im forward-thread omt_xxx --receive-id-type chat_id --receive-id oc_xxx --format json
feishu im update-url-previews --preview-token token_1 --preview-token token_2 --open-id ou_xxx --format json

# 文件与文档
feishu media upload-file ./final.csv --format json
feishu media download-file file_xxx ./downloads/file.bin --format json
feishu media download-file img_v3_xxx ./downloads/image.jpg --format json
# 用户发送的消息资源需带 message_id
feishu media download-file img_v3_xxx ./downloads/image.jpg --message-id om_xxx --resource-type image --format json
feishu bitable create-from-csv ./final.csv --app-name "任务结果" --table-name "结果表"
feishu bitable list-records --app-token app_xxx --table-id tbl_xxx --all --format json
feishu docx create-from-markdown --title "日报" --markdown-file ./report.md
feishu docx get-markdown --doc-token doccn_xxx --doc-type docx --format json
feishu drive grant-edit --token doccn_xxx --resource-type docx --member-id ou_xxx --permission edit --format json

# Wiki
feishu wiki search-nodes --query "项目周报" --all --format json
feishu wiki list-spaces --all --format json

# 搜索
feishu search app --query "审批" --auth-mode user --format json
feishu search message --query "故障" --chat-type group_chat --auth-mode user --format json
feishu search doc-wiki --query "项目周报" --doc-filter-json '{"only_title": true}' --auth-mode user --format json

# 通讯录
feishu contact user get --user-id ou_xxx --user-id-type open_id --format json
feishu contact user by-department --department-id od_xxx --page-size 20 --format json
feishu contact department search --query "研发" --format json
feishu contact scope get --page-size 100 --format json

# 日历
feishu calendar list-calendars --page-size 50 --format json
feishu calendar create-event --calendar-id cal_xxx --event-file ./event.json --format json
feishu calendar attach-material --calendar-id cal_xxx --event-id evt_xxx --path ./agenda.md --format json
```

## User Auth（CLI 最佳实践）

`feishu auth login` 默认走本地回调（`http://127.0.0.1:18080/callback`），并支持 PKCE。

- 第一步：在飞书开发者后台安全设置中添加本地重定向 URL（localhost）
- 第二步：执行 `feishu auth login`
- 第三步：后续直接执行 `feishu auth whoami` 或其它 `auth_mode=user` 命令

自动处理策略：

- access token 临近过期（默认提前 300 秒）会自动 refresh
- 接口返回 token 失效相关错误时会自动 refresh 并重试 1 次
- refresh 成功后会自动更新本地 token store（包含新 refresh token）

## 内容类命令（Agent 建议）

- 分页查询优先使用 `--all`：`bitable list-records`、`wiki list-spaces`、`wiki search-nodes`、`wiki list-nodes`
- `bitable list-records` 现已支持 `--view-id`、`--filter`、`--sort`、`--field-names`、`--text-field-as-array`
- 授权参数已做强约束：`--member-id-type`、`--resource-type`、`--permission`，可减少参数拼写错误
- `docx get-markdown --doc-type` 已限制官方支持值，避免无效文档类型

## 日历附件（Agent 强烈建议）

为避免 `193107 no permission to access attachment file token`，不要手动先传错误上传点再更新日程。

直接使用：

```bash
feishu calendar attach-material --calendar-id cal_xxx --event-id evt_xxx --path ./agenda.md --format json
```

该命令会自动：

- 上传素材时使用 `parent_type=calendar`
- 上传素材时使用 `parent_node=<calendar_id>`
- 更新日程 `attachments`（默认追加模式，可通过 `--mode replace` 覆盖）

## Stdin（Agent 推荐）

很多命令支持直接从标准输入读取，适合 LLM/脚本管道：

```bash
# Markdown from stdin
cat report.md | feishu im send-markdown --receive-id ou_xxx --markdown-stdin --format json

# JSON from stdin
echo '{"text":"hello"}' | feishu im send --receive-id ou_xxx --msg-type text --content-stdin --format json
echo '{"x":1}' | feishu auth request POST /some/path --payload-stdin --format json
```

## 事件与长连接

```bash
# Webhook 工具
feishu webhook parse --body-file ./webhook.json --format json
feishu webhook verify-signature --headers-file ./headers.json --body-file ./raw_body.json --encrypt-key xxx
feishu webhook serve --host 127.0.0.1 --port 8000 --path /webhook/feishu --max-requests 10

# 获取 WS endpoint
feishu ws endpoint --format json

# 低层 WS 监听（可自动退出）
feishu ws run --max-events 1 --output-file ./events.jsonl --format json

# 一站式服务模式（FeishuBotServer）
feishu server run --print-payload --output-file ./events.jsonl

# 后台托管服务
feishu server start --pid-file ./.feishu_server.pid --log-file ./feishu-server.log
feishu server status --pid-file ./.feishu_server.pid --format json
feishu server stop --pid-file ./.feishu_server.pid
```

`ws run` / `server run` 支持：

- `--event-type`：可重复，按事件类型过滤
- `--print-payload`：输出完整 payload
- `--output-file`：JSON Lines 落盘
- `--max-events`：收到 N 个事件后自动停止

`webhook serve` 支持：

- `--encrypt-key` / `--verification-token`
- `--no-verify-signatures`
- `--event-type`、`--print-payload`、`--output-file`
- `--max-requests`：处理 N 个请求后自动退出
