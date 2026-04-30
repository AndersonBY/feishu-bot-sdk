# 16 lark-cli 对齐 Shortcut 域

[English](../en/16-lark-cli-parity-domains.md) | [返回中文索引](../README.md)

对齐基线：`third_party_service/lark-cli` commit `b37adfd`（2026-04-29 20:04:06 +0800，v1.0.22）。生成的对齐报告显示基线 210 个生产 shortcut 已全部覆盖。`feishu-bot-sdk` 当前注册 217 个 shortcut，因为额外保留了 7 个兼容扩展。

## 新覆盖域

| 域 | Shortcut 数 | 覆盖范围 |
| --- | ---: | --- |
| `base` | 75 | 表、字段、视图、记录、base、角色、高级权限、工作流、数据查询、表单、仪表盘 |
| `docs` | 9 | Docs AI 创建/读取/更新/搜索与文档媒体 |
| `whiteboard` | 2 | 白板查询和更新 |
| `slides` | 3 | 演示文稿创建、媒体上传、页面替换 |
| `okr` | 8 | 周期、进展记录、图片上传 |
| `event` | 1 | 事件订阅 / stdin 消费 shortcut |
| `sheets` | 38 | 值、样式、维度、筛选、下拉、媒体、浮动图片 |
| `task` | 18 | 任务更新/搜索、关联任务、任务清单流程 |

## Base

```bash
feishu base +table-list --base-token app_xxx --format json
feishu base +record-search --base-token app_xxx --table-id tbl_xxx --json '{"filter":{"conjunction":"and","conditions":[]}}' --format json
feishu base +record-upsert --base-token app_xxx --table-id tbl_xxx --json '{"fields":{"任务":"完成"}}' --format json
feishu base +dashboard-block-create --base-token app_xxx --dashboard-id dash_xxx --json '{"block_type":"chart"}' --format json
```

写操作前可先加 `--dry-run` 检查请求形态。P7 对齐层重点覆盖 lark-cli 请求构造；高级对象名解析和专门 Base SDK 包属于 parity plan 中的延期增强。

## Docs 和 Whiteboard

```bash
feishu docs +search --query "周报" --format json
feishu docs +create --content '<doc><block type="heading1">日报</block></doc>' --format json
feishu docs +fetch --doc doccn_xxx --doc-format markdown --format json
feishu docs +update --doc doccn_xxx --command append --content '<text>完成</text>' --format json
feishu docs +media-upload --file ./image.png --parent-type docx_image --parent-node doccn_xxx --format json
feishu whiteboard +query --whiteboard-token wb_xxx --output-as image --output ./board.png --format json
feishu whiteboard +update --whiteboard-token wb_xxx --source ./diagram.mmd --input-format mermaid --format json
```

兼容 Docx helper 仍保留为 `docx +convert-content` 和 `docx +insert-content`。

## Sheets 和 Slides

```bash
feishu sheets +read --spreadsheet-token sht_xxx --range Sheet1!A1:B10 --format json
feishu sheets +write --spreadsheet-token sht_xxx --range Sheet1!A1:B2 --values '[[1,2],[3,4]]' --format json
feishu sheets +set-style --spreadsheet-token sht_xxx --range Sheet1!A1:B2 --style '{"font":{"bold":true}}' --format json
feishu sheets +set-dropdown --spreadsheet-token sht_xxx --range Sheet1!A:A --options '["待办","完成"]' --format json
feishu sheets +create-float-image --spreadsheet-token sht_xxx --sheet-id sheet_xxx --image-id img_xxx --format json
feishu slides +create --title "季度复盘" --slides '[{"title":"开场"}]' --format json
feishu slides +media-upload --presentation ppt_xxx --file ./image.png --format json
feishu slides +replace-slide --presentation ppt_xxx --slide-id slide_xxx --parts ./slide.xml --format json
```

## OKR

```bash
feishu okr +cycle-list --user-id ou_xxx --format json
feishu okr +cycle-detail --cycle-id cycle_xxx --user-id ou_xxx --format json
feishu okr +progress-list --target-id obj_xxx --target-type objective --format json
feishu okr +progress-create --target-id obj_xxx --target-type objective --content "进展正常" --progress-percent 80 --format json
feishu okr +upload-image --file ./progress.png --format json
```

## Event

```bash
feishu event list --format json
feishu event schema im.message.receive_v1 --format json
cat ./event.json | feishu event consume im.message.receive_v1 --stdin --format json
feishu event +subscribe --event-types im.message.receive_v1 --output-dir ./events --dry-run --format json
```

`event schema` 会带上从 `lark-cli/internal/event/schemas` commit `b37adfd` 同步来的本地 schema 快照信息。

## 扩展后的 Task

```bash
feishu task +update --task-id task_xxx --summary "更新后的任务" --format json
feishu task +search --query "合同" --page-size 50 --format json
feishu task +set-ancestor --task-id task_xxx --ancestor-id parent_xxx --format json
feishu task +get-related-tasks --task-id task_xxx --format json
feishu task +subscribe-event --resource-type task --resource-id task_xxx --event-type task.updated --format json
feishu task +tasklist-create --name "上线任务" --format json
feishu task +tasklist-task-add --tasklist-id list_xxx --task-id task_xxx --format json
feishu task +tasklist-members --tasklist-id list_xxx --add ou_xxx --format json
```

`task +delete` 作为 SDK 兼容扩展保留，不计入当前 `lark-cli` parity shortcut。

## 已有域的新 Shortcut 示例

```bash
feishu drive +upload --file ./final.csv --folder-token fld_xxx --format json
feishu drive +download --file-token file_xxx --output ./downloads/final.csv --format json
feishu drive +apply-permission --token doc_xxx --type docx --perm view --remark "需要访问" --format json
feishu im +messages-send --chat-id oc_xxx --text "hello" --format json
feishu im +messages-search --query "故障" --format json
feishu calendar +agenda --calendar-id primary --start 1735700400 --end 1735786800 --format json
feishu contact +search-user --query Alice --format json
feishu minutes +search --query "周会" --format json
feishu vc +notes --meeting-id meet_xxx --format json
feishu wiki +node-create --space-id spc_xxx --parent-node-token wiki_xxx --title "Runbook" --format json
feishu mail +triage --mailbox me --folder-id INBOX --query "紧急" --format json
feishu mail +send --mailbox me --to user@example.com --subject "日报" --body-file ./report.html --confirm-send --format json
```

## 兼容扩展

这些命令继续为已有 SDK 用户保留：

- `bitable +create-from-csv`
- `calendar +attach-material`
- `docx +convert-content`
- `docx +insert-content`
- `drive +requester-upload`
- `mail +send-markdown`
- `task +delete`
