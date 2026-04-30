# lark-cli Parity Report

## Summary

| Area | lark-cli | feishu-bot-sdk | Missing |
|---|---:|---:|---:|
| Shortcuts | 210 | 217 | 0 |
| Services | 9 | 9 | 0 |
| Service methods | 120 | 120 | 0 |
| Skills | 23 | 1 | 23 |
| Top-level commands | 24 | 30 | 0 |
| Required metadata files | 14 | 14 | 0 |

## Live Feishu Verification

Latest full live run:

| Field | Value |
|---|---|
| Artifact | `/tmp/feishu-shortcut-live-20260430143224/live_verification_results.json` |
| Total exercised cases | 225 |
| Passed | 107 |
| API-blocked | 118 |
| CLI failed | 0 |
| Internal errors | 0 |

The live matrix used the `default` profile with real Feishu device-flow user authorization and the test enterprise app credentials from the local environment. It exercised every newly aligned shortcut through the CLI against real Feishu APIs. `api_blocked` entries are real Feishu API responses such as permission, parameter, tenant capability, resource availability, invalid fixture token, or formatted HTTP timeout failures; they are not CLI crashes.

Additional verification performed after the full run:

- Targeted download-error rerun: `/tmp/feishu-download-target-live-20260430135216`, summary `api_blocked=4`, `internal_errors=0`.
- Wiki cleanup investigation found Feishu's wiki node delete endpoint requires `obj_type` in the DELETE body and, for these nodes, the path token that succeeds is the node `obj_token`. The live verification runner now records `wiki +node-create` and `wiki +move` outputs for cleanup with `DELETE /wiki/v2/spaces/{space_id}/nodes/{obj_token}`.
- The final live run verified that both Wiki cleanup requests returned success task IDs and follow-up `get_node` checks for the created `obj_token` values returned `131005 not found`.
- A real `minutes +download --minute-tokens invalid_minute` rerun verified that business-field token errors now remain `http_error 99992402` and no longer trigger a user token refresh attempt.

## Missing Shortcuts By Service

| Service | Missing count | Commands |
|---|---:|---|
| none | 0 |  |

## Extra feishu-bot-sdk Shortcuts

- `bitable +create-from-csv`
- `calendar +attach-material`
- `docx +convert-content`
- `docx +insert-content`
- `drive +requester-upload`
- `mail +send-markdown`
- `task +delete`

## Missing Skills

- `lark-approval`
- `lark-attendance`
- `lark-base`
- `lark-calendar`
- `lark-contact`
- `lark-doc`
- `lark-drive`
- `lark-event`
- `lark-im`
- `lark-mail`
- `lark-minutes`
- `lark-okr`
- `lark-openapi-explorer`
- `lark-shared`
- `lark-sheets`
- `lark-skill-maker`
- `lark-slides`
- `lark-task`
- `lark-vc`
- `lark-whiteboard`
- `lark-wiki`
- `lark-workflow-meeting-summary`
- `lark-workflow-standup-report`
