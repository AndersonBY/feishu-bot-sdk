# CLI Command Mapping

This file tracks the main command-shape changes after the `lark-cli` alignment work.

## Top-level model

| Old shape | New shape |
| --- | --- |
| Handwritten domain commands only | `shortcut + service + raw api` |
| `auth request` | `api METHOD /open-apis/...` |
| No `schema` | `schema list/show/paths` |
| No `doctor` | `doctor` |
| No `completion` | `completion bash|zsh|fish|powershell` |

## Identity and auth

| Old | New |
| --- | --- |
| `--auth-mode tenant|user|auto` | `--as bot|user|auto` |
| `default_identity` | `default_as` |
| public `oauth ...` | internal runtime only |

## Workflow commands

| Old command | New preferred command |
| --- | --- |
| `feishu bitable create-from-csv` | `feishu bitable +create-from-csv` |
| `feishu docx convert-content` | `feishu docx +convert-content` |
| `feishu docx insert-content` | `feishu docx +insert-content` |
| `feishu calendar attach-material` | `feishu calendar +attach-material` |
| `feishu drive requester-upload-file` | `feishu drive +requester-upload` |
| `feishu mail message send-markdown` | `feishu mail +send-markdown` |

## Service commands

Generated service commands now use:

```bash
feishu <service> <resource> <method> --params '{"..."}' --data '{"..."}'
```

Examples:

```bash
feishu drive files copy --params '{"file_token":"doc_xxx"}' --data '{"folder_token":"fld_xxx","name":"copy","type":"file"}'
feishu calendar calendars search --data '{"query":"weekly sync"}'
```
