# CLI Command Mapping

This file tracks the command-shape changes after the `lark-cli` parity work. The current baseline is `third_party_service/lark-cli` commit `b37adfd` (2026-04-29 20:04:06 +0800, v1.0.22).

## Top-level Taxonomy

| Category | Commands |
| --- | --- |
| Runtime and diagnostics | `api`, `auth`, `completion`, `doctor`, `schema`, `update` |
| Profile and config | `profile`, `config` |
| Event runtime | `event`, `webhook`, `ws`, `server` |
| Media and Docx helpers | `media`, `docx` |
| Metadata services | `calendar`, `drive`, `im`, `mail`, `minutes`, `sheets`, `task`, `vc`, `wiki` |
| Shortcut-only lark domains | `base`, `contact`, `docs`, `okr`, `slides`, `whiteboard` |
| Compatibility shortcut group | `bitable` |

`feishu` exposes 30 top-level groups. The current parity report shows zero missing top-level groups compared with the baseline.

## Global Runtime Flags

Most commands share these runtime options:

- identity and profile: `--as user|bot|auto`, `--profile`, `--app-id`, `--app-secret`, `--access-token`
- output: `--format json|pretty|table|csv|ndjson|human`, `--jq/-q`, `--save-output`, `--full-output`, `--output-offset`, `--max-output-chars`
- service IO: `--params`, `--data`, `--file`, `--output`, `--dry-run`, `--yes`
- pagination: `--page-all`, `--page-size`, `--page-limit`, `--page-delay`

## Schema Mapping

| Shape | Status |
| --- | --- |
| `feishu schema` | lark-style service list with `source_commit` metadata |
| `feishu schema drive` | lark-style raw service schema |
| `feishu schema drive.files.copy` | lark-style method schema |
| `feishu schema list` | compatibility alias |
| `feishu schema list drive` | compatibility alias with service methods and shortcuts |
| `feishu schema show drive.files.copy` | compatibility alias |
| `feishu schema paths` | compatibility alias |

## Profile and Config Mapping

| lark-style command | Compatibility or old shape |
| --- | --- |
| `feishu profile list` | `feishu config list-profiles` |
| `feishu profile add --name NAME --app-id cli_xxx --app-secret-stdin` | `feishu config init --profile NAME ...` |
| `feishu profile use NAME` | `feishu config set-default-profile NAME` |
| `feishu profile remove NAME` | `feishu config remove-profile NAME` |
| `feishu profile rename OLD NEW` | no old direct equivalent |
| `feishu config bind --source openclaw --identity user-default` | new lark-style binding helper |
| `feishu config strict-mode true|false` | new strict-mode helper |

## Update and Event Mapping

| Command | Purpose |
| --- | --- |
| `feishu update --check --format json` | report installed package version and package-manager hint |
| `feishu update --force --format json` | show reinstall/update instructions even when current |
| `feishu event list --format json` | list local event definitions |
| `feishu event schema im.message.receive_v1 --format json` | emit local event schema with the synced event schema snapshot |
| `feishu event consume im.message.receive_v1 --stdin --format json` | consume one event payload from stdin |
| `feishu event status --format json` | inspect local placeholder state |
| `feishu event stop --format json` | mark local placeholder state stopped |
| `feishu event +subscribe ...` | lark shortcut shape for event subscription/stdin consumption |

## Shortcut Domains

| Domain | Count | Examples |
| --- | ---: | --- |
| `base` | 75 | `+table-list`, `+record-upsert`, `+dashboard-block-create` |
| `calendar` | 8 | `+agenda`, `+create`, `+freebusy`, `+room-find`, `+suggestion`, `+update` |
| `contact` | 2 | `+get-user`, `+search-user` |
| `docs` | 9 | `+create`, `+fetch`, `+update`, `+media-upload`, `+whiteboard-update` |
| `drive` | 14 | `+upload`, `+download`, `+delete`, `+create-folder`, `+search` |
| `event` | 1 | `+subscribe` |
| `im` | 10 | `+chat-create`, `+messages-send`, `+messages-search`, `+threads-messages-list` |
| `mail` | 18 | `+message`, `+messages`, `+triage`, `+send`, `+reply-all`, `+template-update` |
| `minutes` | 2 | `+search`, `+download` |
| `okr` | 8 | `+cycle-list`, `+progress-create`, `+upload-image` |
| `sheets` | 38 | `+read`, `+write`, `+set-style`, `+set-dropdown`, `+create-float-image` |
| `slides` | 3 | `+create`, `+media-upload`, `+replace-slide` |
| `task` | 18 | `+create`, `+update`, `+search`, `+tasklist-create`, `+tasklist-members` |
| `vc` | 3 | `+search`, `+notes`, `+recording` |
| `whiteboard` | 2 | `+query`, `+update` |
| `wiki` | 3 | `+move`, `+node-create`, `+delete-space` |

## Compatibility Extensions

These commands intentionally remain available but are not counted as current `lark-cli` parity commands:

| Compatibility command | Preferred reason to keep it |
| --- | --- |
| `feishu bitable +create-from-csv` | existing SDK CSV-to-Bitable workflow |
| `feishu calendar +attach-material` | safer calendar attachment workflow |
| `feishu docx +convert-content` | SDK content conversion helper |
| `feishu docx +insert-content` | SDK Markdown/HTML insertion helper |
| `feishu drive +requester-upload` | requester-owned upload workflow |
| `feishu mail +send-markdown` | Markdown mail rendering helper |
| `feishu task +delete` | SDK task deletion compatibility |

## Service Commands

Generated service commands use:

```bash
feishu <service> <resource> <method> --params '{"..."}' --data '{"..."}'
```

Examples:

```bash
feishu drive files copy --params '{"file_token":"doc_xxx"}' --data '{"folder_token":"fld_xxx","name":"copy","type":"file"}'
feishu calendar calendars search --data '{"query":"weekly sync"}'
```
