# 16 lark-cli Parity Shortcut Domains

[中文](../zh/16-lark-cli-parity-domains.md) | [Back to English Index](../README_EN.md)

Baseline: `third_party_service/lark-cli` commit `b37adfd` (2026-04-29 20:04:06 +0800, v1.0.22). The generated report shows 210/210 baseline production shortcuts covered. `feishu-bot-sdk` registers 217 shortcuts because it also keeps 7 compatibility extensions.

## Newly Covered Domains

| Domain | Shortcut count | Coverage |
| --- | ---: | --- |
| `base` | 75 | table, field, view, record, base, role, advanced permission, workflow, data query, form, dashboard |
| `docs` | 9 | Docs AI create/fetch/update/search and document media |
| `whiteboard` | 2 | whiteboard query and update |
| `slides` | 3 | presentation create, media upload, slide replacement |
| `okr` | 8 | cycles, progress records, image upload |
| `event` | 1 | event subscription/stdin consumption shortcut |
| `sheets` | 38 | values, styles, dimensions, filters, dropdowns, media, float images |
| `task` | 18 | task mutation/search, related tasks, tasklist flows |

## Base

```bash
feishu base +table-list --base-token app_xxx --format json
feishu base +record-search --base-token app_xxx --table-id tbl_xxx --json '{"filter":{"conjunction":"and","conditions":[]}}' --format json
feishu base +record-upsert --base-token app_xxx --table-id tbl_xxx --json '{"fields":{"Task":"Done"}}' --format json
feishu base +dashboard-block-create --base-token app_xxx --dashboard-id dash_xxx --json '{"block_type":"chart"}' --format json
```

Use `--dry-run` to inspect request shape before write operations. The P7 parity layer focuses on lark-cli request construction; advanced object-name resolution and deep Base SDK wrappers are tracked as deferred enhancements in the parity plan.

## Docs and Whiteboard

```bash
feishu docs +search --query "weekly report" --format json
feishu docs +create --content '<doc><block type="heading1">Daily Report</block></doc>' --format json
feishu docs +fetch --doc doccn_xxx --doc-format markdown --format json
feishu docs +update --doc doccn_xxx --command append --content '<text>Done</text>' --format json
feishu docs +media-upload --file ./image.png --parent-type docx_image --parent-node doccn_xxx --format json
feishu whiteboard +query --whiteboard-token wb_xxx --output-as image --output ./board.png --format json
feishu whiteboard +update --whiteboard-token wb_xxx --source ./diagram.mmd --input-format mermaid --format json
```

Compatibility Docx helpers remain available as `docx +convert-content` and `docx +insert-content`.

## Sheets and Slides

```bash
feishu sheets +read --spreadsheet-token sht_xxx --range Sheet1!A1:B10 --format json
feishu sheets +write --spreadsheet-token sht_xxx --range Sheet1!A1:B2 --values '[[1,2],[3,4]]' --format json
feishu sheets +set-style --spreadsheet-token sht_xxx --range Sheet1!A1:B2 --style '{"font":{"bold":true}}' --format json
feishu sheets +set-dropdown --spreadsheet-token sht_xxx --range Sheet1!A:A --options '["Todo","Done"]' --format json
feishu sheets +create-float-image --spreadsheet-token sht_xxx --sheet-id sheet_xxx --image-id img_xxx --format json
feishu slides +create --title "Quarterly Review" --slides '[{"title":"Intro"}]' --format json
feishu slides +media-upload --presentation ppt_xxx --file ./image.png --format json
feishu slides +replace-slide --presentation ppt_xxx --slide-id slide_xxx --parts ./slide.xml --format json
```

## OKR

```bash
feishu okr +cycle-list --user-id ou_xxx --format json
feishu okr +cycle-detail --cycle-id cycle_xxx --user-id ou_xxx --format json
feishu okr +progress-list --target-id obj_xxx --target-type objective --format json
feishu okr +progress-create --target-id obj_xxx --target-type objective --content "On track" --progress-percent 80 --format json
feishu okr +upload-image --file ./progress.png --format json
```

## Event

```bash
feishu event list --format json
feishu event schema im.message.receive_v1 --format json
cat ./event.json | feishu event consume im.message.receive_v1 --stdin --format json
feishu event +subscribe --event-types im.message.receive_v1 --output-dir ./events --dry-run --format json
```

`event schema` includes a local snapshot synced from `lark-cli/internal/event/schemas` at commit `b37adfd`.

## Expanded Task

```bash
feishu task +update --task-id task_xxx --summary "Updated task" --format json
feishu task +search --query "contract" --page-size 50 --format json
feishu task +set-ancestor --task-id task_xxx --ancestor-id parent_xxx --format json
feishu task +get-related-tasks --task-id task_xxx --format json
feishu task +subscribe-event --resource-type task --resource-id task_xxx --event-type task.updated --format json
feishu task +tasklist-create --name "Launch tasks" --format json
feishu task +tasklist-task-add --tasklist-id list_xxx --task-id task_xxx --format json
feishu task +tasklist-members --tasklist-id list_xxx --add ou_xxx --format json
```

`task +delete` is retained as an SDK compatibility extension and is not counted as a current `lark-cli` parity shortcut.

## Existing Domains With Expanded Shortcuts

```bash
feishu drive +upload --file ./final.csv --folder-token fld_xxx --format json
feishu drive +download --file-token file_xxx --output ./downloads/final.csv --format json
feishu drive +apply-permission --token doc_xxx --type docx --perm view --remark "Need access" --format json
feishu im +messages-send --chat-id oc_xxx --text "hello" --format json
feishu im +messages-search --query "incident" --format json
feishu calendar +agenda --calendar-id primary --start 1735700400 --end 1735786800 --format json
feishu contact +search-user --query Alice --format json
feishu minutes +search --query "weekly sync" --format json
feishu vc +notes --meeting-id meet_xxx --format json
feishu wiki +node-create --space-id spc_xxx --parent-node-token wiki_xxx --title "Runbook" --format json
feishu mail +triage --mailbox me --folder-id INBOX --query "urgent" --format json
feishu mail +send --mailbox me --to user@example.com --subject "Daily Report" --body-file ./report.html --confirm-send --format json
```

## Compatibility Extensions

These remain supported for existing SDK users:

- `bitable +create-from-csv`
- `calendar +attach-material`
- `docx +convert-content`
- `docx +insert-content`
- `drive +requester-upload`
- `mail +send-markdown`
- `task +delete`
