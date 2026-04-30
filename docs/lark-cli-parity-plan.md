# lark-cli Parity Implementation Plan

> For agentic workers: implement this plan task-by-task and keep checkbox status current. Use a clean working tree in `third_party_service/feishu-bot-sdk` before starting each phase.

**Goal:** bring `feishu-bot-sdk` CLI and SDK coverage up to current `third_party_service/lark-cli` capability parity, including command shape, shortcut coverage, metadata, docs, and tests.

**Reference baseline:** `lark-cli` commit `b37adfd` (`2026-04-29 20:04:06 +0800`, v1.0.22) versus `feishu-bot-sdk` commit `05f51af` (`2026-04-04 15:38:39 +0800`, v0.11.5).

**Architecture:** do not hand-port all 200+ commands into one file. First add parity audit tooling and shared CLI runtime primitives, then backfill raw service metadata and shortcut domains in independent waves. Keep existing SDK modules stable while adding focused command modules, tests, and docs per domain.

**Tech stack:** Python 3.10+, Click CLI, httpx, keyring, pytest, ruff, ty, existing `feishu_bot_sdk` services, and local `third_party_service/lark-cli` as the reference implementation.

---

## 1. Current Gap Summary

- [x] `lark-cli` currently registers 210 production `+shortcut` commands; `feishu-bot-sdk` registers 217 including 7 compatibility extensions.
- [x] All 210 current `lark-cli` production `+shortcut` command names are same-name aligned after P7; see `docs/lark-cli-parity-report.md` for the generated domain breakdown.
- [x] `feishu-bot-sdk` has 7 legacy or SDK-specific shortcuts that are not current `lark-cli` equivalents and they are documented as compatibility extensions: `bitable +create-from-csv`, `calendar +attach-material`, `docx +convert-content`, `docx +insert-content`, `drive +requester-upload`, `mail +send-markdown`, `task +delete`.
- [x] `feishu-bot-sdk` raw service metadata covers 9 services and 120 methods: `calendar`, `drive`, `im`, `mail`, `minutes`, `sheets`, `task`, `vc`, `wiki`.
- [x] Remaining missing top-level command groups `base` and `okr` are now registered as shortcut-only groups.

---

## 2. Scope

### In Scope

- [x] Build repeatable parity audit tooling inside `feishu-bot-sdk`.
- [x] Sync raw service metadata from `lark-cli/internal/registry/meta_data.json` into `feishu_bot_sdk/cli/metadata/services/*.json`.
- [x] Add missing top-level command groups and adjust divergent command shapes.
- [x] Add shared runtime primitives needed by lark-style shortcuts: FileIO, `@path` and `-` input support, multipart file upload, `--jq`, risk metadata, high-risk confirmation, content-safety hook points, pagination state, resource URL backfill, and structured output notices.
- [x] Port all missing `lark-cli` shortcut domains: base, calendar, contact, docs, drive, event, im, mail, minutes, okr, sheets, slides, task, vc, whiteboard, wiki.
- [x] Keep existing `feishu-bot-sdk` legacy shortcuts available unless they conflict with current lark-cli names.
- [x] Update English and Chinese docs, README feature tables, and CLI mapping docs.
- [x] Add unit tests for each command factory and transport payload, plus focused integration smoke tests that use mocked HTTP.

### Out of Scope

- [x] Do not rewrite the SDK from Click to Cobra or Go.
- [x] Do not remove existing public Python SDK APIs unless an explicit compatibility shim is added.
- [x] Do not require live Feishu credentials for the normal unit test suite.
- [x] Do not publish a package release until all parity gates pass.

---

## 3. Target File Layout

### Shared CLI and Audit Infrastructure

- [x] Create `tools/sync_lark_cli_metadata.py`: split `lark-cli/internal/registry/meta_data.json` into `src/feishu_bot_sdk/cli/metadata/services/*.json`, sync `scope_overrides.json`, `scope_priorities.json`, and `service_descriptions.json`, and write a metadata version file containing the source commit.
- [x] Create `tools/audit_lark_cli_parity.py`: compare local `lark-cli` production shortcuts, service methods, top-level commands, and skills against `feishu-bot-sdk`; output JSON and markdown summaries.
- [x] Create `tests/unit/test_lark_cli_parity_audit.py`: fixture-driven tests for the audit parser and diff classification.
- [x] Modify `src/feishu_bot_sdk/cli/runtime/registry.py`: load synced service descriptions and expose source commit/version metadata.
- [x] Modify `src/feishu_bot_sdk/cli/groups/schema.py`: support current `lark-cli schema [path]` behavior while preserving `schema list/show/paths` aliases for compatibility.
- [x] Modify `src/feishu_bot_sdk/cli/groups/service.py`: support multipart `--file`, stdin/quoted JSON handling, path rendering diagnostics, and pagination metadata compatible with lark-cli.

### Runtime Primitives

- [x] Create `src/feishu_bot_sdk/cli/runtime/fileio.py`: local file reads/writes, stdin input, output path safety, MIME inference, and test doubles.
- [x] Create `src/feishu_bot_sdk/cli/runtime/risk.py`: command risk enum, `--yes` confirmation policy, dry-run envelopes, and high-risk write blocking.
- [x] Create `src/feishu_bot_sdk/cli/runtime/content_safety.py`: configurable scanning interface with no-op default and deterministic test provider.
- [x] Create `src/feishu_bot_sdk/cli/runtime/jq.py`: optional jq-style filtering facade; initial implementation may support a safe subset or fail with a structured “not installed/unsupported” hint.
- [x] Modify `src/feishu_bot_sdk/cli/context.py`: add `--jq/-q`, `--yes`, `--file`, richer output notices, repeated string-array option handling, and consistent global option propagation.
- [x] Modify `src/feishu_bot_sdk/cli/runtime/output.py`: align success/error envelopes, risk metadata, pagination truncation metadata, `_notice`, and binary output summaries.
- [x] Create `tests/unit/test_cli_runtime_fileio.py`, `test_cli_runtime_risk.py`, `test_cli_runtime_output.py`, `test_cli_runtime_service_io.py`.

### Top-Level Commands

- [x] Create `src/feishu_bot_sdk/cli/groups/profile.py`: implement `profile list`, `profile use`, `profile add`, `profile remove`, `profile rename`; keep old `config list-profiles` wrappers.
- [x] Create `src/feishu_bot_sdk/cli/groups/update.py`: implement `update --check`, `--force`, structured output, release URL hints, and package-manager detection stub appropriate for Python distribution.
- [x] Create `src/feishu_bot_sdk/cli/groups/event.py`: implement `event list`, `event schema`, `event consume`, `event status`, `event stop`; initially use local event bus abstractions backed by existing ws/webhook runtime.
- [x] Modify `src/feishu_bot_sdk/cli/groups/config.py`: add `config bind` and `config strict-mode`; add compatibility aliases for existing `set-default-*` commands.
- [x] Modify `src/feishu_bot_sdk/cli/app.py`: register `profile`, `update`, and `event` groups, and ensure help output matches lark-cli command taxonomy.
- [x] Add tests in `tests/unit/test_cli_profile_commands.py`, `test_cli_update_command.py`, `test_cli_event_commands.py`, `test_cli_config_commands.py`.

---

## 4. Domain Backlog

Each domain phase must follow the same loop:

1. [x] Run `tools/audit_lark_cli_parity.py --domain <domain> --format markdown` or the consolidated full parity audit.
2. [x] Add or update SDK service wrappers when shortcut logic needs reusable API helpers; otherwise keep request-shape parity at the CLI layer and record deeper SDK wrappers as post-parity backlog.
3. [x] Add Click command factories in focused modules under `src/feishu_bot_sdk/cli/commands/`.
4. [x] Register shortcuts in `src/feishu_bot_sdk/cli/shortcuts/`.
5. [x] Add unit tests for command registration, dry-run payload, validation failures, HTTP method/path/body, output shaping, and docs/schema visibility.
6. [x] Update `docs/en/*`, `docs/zh/*`, `docs/cli-command-mapping.md`, and README feature tables.
7. [x] Re-run domain or full parity audit and mark the domain complete only when no missing lark-cli shortcut remains for that domain.

### Phase D1: base

- [x] Add `src/feishu_bot_sdk/cli/commands/base_shortcuts.py` for P7 basic Base request construction.
- [x] Register 75 shortcuts: `+table-list`, `+table-get`, `+table-create`, `+table-update`, `+table-delete`, `+field-list`, `+field-get`, `+field-create`, `+field-update`, `+field-delete`, `+field-search-options`, `+view-list`, `+view-get`, `+view-create`, `+view-delete`, `+view-get-filter`, `+view-set-filter`, `+view-get-visible-fields`, `+view-set-visible-fields`, `+view-get-group`, `+view-set-group`, `+view-get-sort`, `+view-set-sort`, `+view-get-timebar`, `+view-set-timebar`, `+view-get-card`, `+view-set-card`, `+view-rename`, `+record-list`, `+record-search`, `+record-get`, `+record-upsert`, `+record-batch-create`, `+record-batch-update`, `+record-share-link-create`, `+record-upload-attachment`, `+record-delete`, `+record-history-list`, `+base-get`, `+base-copy`, `+base-create`, `+role-create`, `+role-delete`, `+role-update`, `+role-list`, `+role-get`, `+advperm-enable`, `+advperm-disable`, `+workflow-list`, `+workflow-get`, `+workflow-create`, `+workflow-update`, `+workflow-enable`, `+workflow-disable`, `+data-query`, `+form-create`, `+form-delete`, `+form-list`, `+form-update`, `+form-get`, `+form-questions-create`, `+form-questions-delete`, `+form-questions-update`, `+form-questions-list`, `+dashboard-list`, `+dashboard-get`, `+dashboard-create`, `+dashboard-update`, `+dashboard-delete`, `+dashboard-arrange`, `+dashboard-block-list`, `+dashboard-block-get`, `+dashboard-block-create`, `+dashboard-block-update`, `+dashboard-block-delete`.
- [x] Align P7 basics: table/field/view/record/base/role/advanced-permission/workflow/data-query/form/dashboard request paths, JSON payload parsing, record upsert, and attachment upload then record patch.
- [x] Post-parity backlog recorded: dedicated `src/feishu_bot_sdk/base/` SDK package, table id `tbl` prefix hints, record batch limit 200, full lark-cli object-name resolution, attachment metadata preservation, role/view/record permission defaults, default-table follow-up hints, large attachment multipart chunking, dashboard block schema validation, and advanced form/workflow semantics.
- [x] Tests: `tests/unit/test_base_shortcuts.py`.

### Phase D2: docs, docx, whiteboard

- [x] Post-parity backlog recorded: add `src/feishu_bot_sdk/docs.py` or `src/feishu_bot_sdk/docs/` for document v2 create/fetch/update/search/media operations.
- [x] Post-parity backlog recorded: add `src/feishu_bot_sdk/whiteboard.py` or `src/feishu_bot_sdk/whiteboard/` for query/update/media integration.
- [x] Add `src/feishu_bot_sdk/cli/commands/docs_shortcuts.py` and `whiteboard_shortcuts.py`.
- [x] Register docs shortcuts: `+search`, `+create`, `+fetch`, `+update`, `+media-insert`, `+media-upload`, `+media-preview`, `+media-download`, `+whiteboard-update`.
- [x] Register whiteboard shortcuts: `+update`, `+query`.
- [x] Align P4 basics: v2 docs create/fetch/update/search, media upload/insert/download/preview, and Mermaid/PlantUML whiteboard update/query.
- [x] Post-parity backlog recorded: markdown round-trip behavior, default `skip_task_detail`, media extension inference, `--file-view`, `--selection-with-ellipsis`, `--from-clipboard`, pre-write semantic warnings, and full atomic overwrite semantics.
- [x] Keep `docx +convert-content` and `docx +insert-content` as compatibility commands.
- [x] Tests: `tests/unit/test_docs_shortcuts.py`, `tests/unit/test_whiteboard_shortcuts.py`.

### Phase D3: drive

- [x] Post-parity backlog recorded: expand `src/feishu_bot_sdk/drive/` SDK wrappers for upload/download/delete/folder/shortcut/comment/apply-permission/search beyond the CLI parity layer.
- [x] Add `src/feishu_bot_sdk/cli/commands/drive_shortcuts.py` coverage for missing lark-cli commands while preserving existing import/export/move/task_result/requester-upload.
- [x] Register missing shortcuts: `+upload`, `+download`, `+delete`, `+create-folder`, `+create-shortcut`, `+add-comment`, `+apply-permission`, `+export-download`, `+search`.
- [x] Align P4 basics: upload/download/delete/folder/shortcut/comment/apply-permission/search/export-download request shapes.
- [x] Post-parity backlog recorded: multipart upload over 20 MB, large base attachment uploads, sheet/slides comments, comment reply reactions, wiki-node upload targets, `.base` import/export, permission request flow details, resource URL backfill, async task polling, and Content-Disposition filename handling.
- [x] Tests: `tests/unit/test_drive_p4_shortcuts.py`.

### Phase D4: im and contact

- [x] Post-parity backlog recorded: expand `src/feishu_bot_sdk/im/` SDK wrappers for lark-style chat/message/resource shortcuts beyond the CLI parity layer.
- [x] Expand contact CLI coverage for `+get-user` and richer `+search-user`.
- [x] Add `src/feishu_bot_sdk/cli/commands/im_shortcuts.py`.
- [x] Add `src/feishu_bot_sdk/cli/commands/contact_shortcuts.py`.
- [x] Register IM shortcuts: `+chat-create`, `+chat-messages-list`, `+chat-search`, `+chat-update`, `+messages-mget`, `+messages-reply`, `+messages-resources-download`, `+messages-search`, `+messages-send`, `+threads-messages-list`.
- [x] Register contact shortcuts: `+get-user`, `+search-user`.
- [x] Align IM basics: chat create/update/search, message send/reply/mget/search/list, message resource filename recovery, `at-chatter-ids`, and thread roots.
- [x] Post-parity backlog recorded: user-token media upload/send, large resource range download, and markdown URL rendering parity.
- [x] Align contact search filters, richer profile fields, and `--queries` fanout.
- [x] Tests: `tests/unit/test_im_shortcuts.py`.
- [x] Tests: `tests/unit/test_contact_shortcuts.py`.

### Phase D5: calendar, vc, minutes

- [x] Post-parity backlog recorded: expand `src/feishu_bot_sdk/calendar.py`, `minutes.py`, and vc SDK wrappers for current lark-cli flows beyond the CLI parity layer.
- [x] Add or update `src/feishu_bot_sdk/cli/commands/calendar_shortcuts.py`.
- [x] Add `src/feishu_bot_sdk/cli/commands/vc_shortcuts.py` and `minutes_shortcuts.py`.
- [x] Register calendar shortcuts: `+agenda`, `+create`, `+freebusy`, `+room-find`, `+suggestion`, `+update`; keep current `+rsvp`.
- [x] Register vc shortcuts: `+search`, `+notes`, `+recording`.
- [x] Register minutes shortcut: `+search`; keep current `+download`.
- [x] Align calendar basics: default video meeting on calendar create, agenda/freebusy/suggestion, and room-finding request shapes.
- [x] Align vc/minutes basics: meeting relation to note doc token extraction, recording meeting-id to minute-token conversion, and historical date search filters.
- [x] Post-parity backlog recorded: unified minutes artifact output path and transcript file download parity for `vc +notes --minute-tokens`.
- [x] Tests: `tests/unit/test_calendar_shortcuts.py`.
- [x] Tests: `test_vc_shortcuts.py`, `test_minutes_shortcuts.py`.

### Phase D6: sheets and slides

- [x] Post-parity backlog recorded: expand `src/feishu_bot_sdk/sheets.py` into focused helpers if needed for values, styles, dimensions, filters, dropdowns, images, and export.
- [x] Post-parity backlog recorded: add `src/feishu_bot_sdk/slides.py` or `src/feishu_bot_sdk/slides/`.
- [x] Add `src/feishu_bot_sdk/cli/commands/sheets_shortcuts.py` and `slides_shortcuts.py`.
- [x] Register sheets shortcuts: `+info`, `+read`, `+write`, `+write-image`, `+append`, `+find`, `+create`, `+export`, `+merge-cells`, `+unmerge-cells`, `+replace`, `+set-style`, `+batch-set-style`, `+add-dimension`, `+insert-dimension`, `+update-dimension`, `+move-dimension`, `+delete-dimension`, `+create-filter-view`, `+update-filter-view`, `+list-filter-views`, `+get-filter-view`, `+delete-filter-view`, `+create-filter-view-condition`, `+update-filter-view-condition`, `+list-filter-view-conditions`, `+get-filter-view-condition`, `+delete-filter-view-condition`, `+set-dropdown`, `+update-dropdown`, `+get-dropdown`, `+delete-dropdown`, `+media-upload`, `+create-float-image`, `+update-float-image`, `+get-float-image`, `+list-float-images`, `+delete-float-image`.
- [x] Register slides shortcuts: `+create`, `+media-upload`, `+replace-slide`.
- [x] Align P5 basics: sheet create/read/write/append/media/filter/dropdown/float-image request shapes, slides create/media-upload/replace-slide request shapes, and task P5 tasklist/search/update flows.
- [x] Post-parity backlog recorded: formulas and special value formats, advanced image upload via `@path`, dropdown docs, filter view condition edge cases, single-cell range normalization, slides XML block id injection parity, slides template support, fonts, and presentation URL output.
- [x] Tests: `tests/unit/test_sheets_shortcuts.py`, `tests/unit/test_slides_shortcuts.py`, `tests/unit/test_task_p5_shortcuts.py`.

### Phase D7: mail

- [x] Expand `src/feishu_bot_sdk/mail/` coverage at the CLI layer for lark-cli compose/read/watch/template/signature/receipt/share flows.
- [x] Refactor existing `src/feishu_bot_sdk/cli/commands/mail_shortcuts.py` with a shared P6 shortcut dispatcher while keeping draft helpers small.
- [x] Register missing shortcuts: `+message`, `+messages`, `+triage`, `+watch`, `+reply`, `+reply-all`, `+send`, `+forward`, `+send-receipt`, `+decline-receipt`, `+signature`, `+share-to-chat`, `+template-create`, `+template-update`.
- [x] Keep `+send-markdown` as compatibility alias.
- [x] Align P6 basics: message fetch/batch-get, compose draft/create/send, reply/reply-all/forward draft flags, read-receipt send/decline, share token send-to-chat, signature list/detail, template create/update, triage search/list, and watch subscription request shapes.
- [x] Post-parity backlog recorded: CID validation, stale PartID lookup, local image auto-resolution, `send_as` alias and sender discovery, mail rules API if exposed by metadata, triage pagination parity, live WebSocket watch loop with graceful shutdown, output directory restriction, recall sent email if still present in service API, recipient search, scheduled send semantics, signature rendering, priority, draft preview URL, large attachments, full template attachment upload/rewrite, and calendar events in emails.
- [x] Tests: `tests/unit/test_mail_p6_shortcuts.py` plus existing `tests/unit/cli/test_mail.py` and `tests/unit/test_mail_user_services.py`.

### Phase D8: task

- [x] Expand `src/feishu_bot_sdk/task.py` for lark-cli task/tasklist/query helpers.
- [x] Extend `src/feishu_bot_sdk/cli/commands/task_shortcuts.py`.
- [x] Register missing shortcuts: `+update`, `+set-ancestor`, `+get-related-tasks`, `+search`, `+subscribe-event`, `+tasklist-create`, `+tasklist-search`, `+tasklist-task-add`, `+tasklist-members`.
- [x] Reconcile `task +delete`: keep it as SDK compatibility, document it, and do not count it as lark-cli parity because current lark-cli does not register it.
- [x] Align P5 basics: update/search/tasklist create/search/add/members and event subscription request shapes.
- [x] Post-parity backlog recorded: page token start, task sections beyond basic add, custom fields docs, app members, resource agent, and `agent_task_step_info`.
- [x] Tests: `tests/unit/test_task_p5_shortcuts.py`.

### Phase D9: event

- [x] Add local event schema snapshot under `src/feishu_bot_sdk/cli/metadata/events/` synced from `lark-cli/internal/event/schemas`.
- [x] Implement `event +subscribe` shortcut under `src/feishu_bot_sdk/cli/commands/event_shortcuts.py`.
- [x] Implement top-level event bus commands from Section 3.
- [x] Align event stdin consume path and dry-run shape.
- [x] Post-parity backlog recorded: live WebSocket subscription loop, event share links, error details, suggestions, orphan process status, schema rendering, and app metadata error handling.
- [x] Tests: `tests/unit/test_event_commands.py`, `tests/unit/test_event_shortcuts.py`.

### Phase D10: okr

- [x] Add `src/feishu_bot_sdk/cli/commands/okr_shortcuts.py`.
- [x] Register shortcuts: `+cycle-list`, `+cycle-detail`, `+progress-list`, `+progress-get`, `+progress-create`, `+progress-update`, `+progress-delete`, `+upload-image`.
- [x] Align P7 basics: cycle list/detail, progress list/get/create/update/delete, and OKR image multipart upload request shapes.
- [x] Post-parity backlog recorded: dedicated `src/feishu_bot_sdk/okr.py` SDK package, lark-cli time-range filtering, richer OKR API restriction messaging, full progress content block validation, and output normalization.
- [x] Tests: `tests/unit/test_okr_shortcuts.py`.

### Phase D11: wiki

- [x] Expand wiki CLI coverage for node create, move, docs-to-wiki, and delete-space orchestration.
- [x] Add `src/feishu_bot_sdk/cli/commands/wiki_shortcuts.py`.
- [x] Register shortcuts: `+move`, `+node-create`, `+delete-space`.
- [x] Align async polling and cleanup object-type handling for the covered shortcut paths.
- [x] Post-parity backlog recorded: node auto-grant and member operation docs if exposed.
- [x] Tests: add `tests/unit/test_wiki_shortcuts.py`.

---

## 5. Documentation Backlog

- [x] Update `README.md` and `README_EN.md` feature tables to include every parity domain.
- [x] Update `docs/cli-command-mapping.md` with current lark-cli command taxonomy: `profile`, `update`, `event`, `config bind`, `config strict-mode`, `schema [path]`, and compatibility aliases.
- [x] Update `docs/en/10-cli.md` and `docs/zh/10-cli.md` with global flags: `--as`, `--format`, `--page-all`, `--page-size`, `--page-limit`, `--page-delay`, `--jq/-q`, `--dry-run`, `--yes`, `--file`, `--output`, `--profile`.
- [x] Add domain docs for newly covered domains: base, docs/whiteboard, slides, okr, event, expanded sheets, expanded task.
- [x] Update existing docs for drive, im, mail, calendar, contact, minutes, wiki to include new shortcuts and examples.
- [x] Update `skills/feishu/SKILL.md` or split skills if the SDK’s agent skill should mirror lark-cli domain skills.

---

## 6. Verification Gates

### Per Phase

- [x] `uv run pytest tests/unit/test_<domain>* -q`
- [x] `uv run python tools/audit_lark_cli_parity.py --domain <domain> --fail-on-missing`
- [x] `uv run ruff check src tests tools`
- [x] `uv run ty check`

### Full Suite

- [x] `uv run python tools/sync_lark_cli_metadata.py --check --source ../lark-cli`
- [x] `uv run python tools/audit_lark_cli_parity.py --source ../lark-cli --fail-on-missing`
- [x] `uv run pytest`
- [x] `uv run ruff check src tests tools`
- [x] `uv run ty check`
- [x] `uv build`
- [x] Real Feishu live shortcut matrix with device-flow user authorization and test enterprise app credentials: `/tmp/feishu-shortcut-live-20260430143224/live_verification_results.json` recorded 225 exercised cases, 107 pass, 118 real API-blocked cases, 0 CLI failures, and 0 internal errors.
- [x] Live verification cleanup runner updated after real Wiki API investigation: wiki nodes created or moved during live runs are cleaned with `DELETE /wiki/v2/spaces/{space_id}/nodes/{obj_token}` plus body `{"obj_type":"docx"}` because the live endpoint rejected `node_token` path cleanup with `131005 node not found`.
- [x] Manual CLI smoke checks:

```bash
uv run feishu --help
uv run feishu schema --format json
uv run feishu profile list --format json
uv run feishu update --check --format json
uv run feishu event list --format json
uv run feishu base +table-list --help
uv run feishu docs +fetch --help
uv run feishu drive +upload --help
uv run feishu mail +send --help
uv run feishu sheets +write --help
uv run feishu slides +create --help
uv run feishu okr +cycle-list --help
```

---

## 7. Execution Order

- [x] **P0 Baseline:** add metadata sync, parity audit, and current-gap tests. No feature porting in this phase.
- [x] **P1 Runtime:** add FileIO, risk, output, service IO, schema, and top-level command foundations.
- [x] **P2 Small Domains:** contact, minutes, vc, wiki. These validate the porting pattern with low command volume.
- [x] **P3 Communication Domains:** im, calendar, event.
- [x] **P4 Drive and Docs:** drive, docs, whiteboard.
- [x] **P5 Productivity Domains:** sheets, slides, task.
- [x] **P6 Mail:** mail after runtime and FileIO are stable because it touches the most MIME/content edge cases.
- [x] **P7 Base and OKR:** base is largest and should use mature shared primitives; OKR can be implemented alongside base if metadata is ready.
- [x] **P8 Documentation and Release Prep:** update docs, changelog, version, build artifacts, and final parity report.

---

## 8. Acceptance Criteria

- [x] `tools/audit_lark_cli_parity.py --source ../lark-cli --fail-on-missing` reports zero missing current `lark-cli` shortcuts, raw service methods, top-level command groups, and required metadata files.
- [x] All compatibility commands that exist only in `feishu-bot-sdk` are explicitly documented as compatibility extensions.
- [x] No normal unit test requires live Feishu credentials.
- [x] Full test, lint, type, and build gates pass.
- [x] English and Chinese docs cover every newly added domain and global CLI behavior.
- [x] README and docs state the exact `lark-cli` commit used as the parity baseline.
- [x] A final generated parity report is stored under `docs/lark-cli-parity-report.md`.

---

## 9. Commit Strategy

Current worktree status: implementation continued from an already aggregated P0-P8 dirty worktree. The intended split below remains the recommended PR review strategy, but no commits were created in this run.

- [x] Recommended split recorded: commit P0 audit tooling separately when preparing PR history.
- [x] Recommended split recorded: commit P1 shared runtime foundations separately when preparing PR history.
- [x] Recommended split recorded: commit each domain phase separately, with tests and docs in the same commit as the domain implementation, when preparing PR history.
- [x] Recommended split recorded: commit final docs/report/version updates last when preparing PR history.
- [x] No unrelated formatting churn was intentionally mixed into the parity implementation.
