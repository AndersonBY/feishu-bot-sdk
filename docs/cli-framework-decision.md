# CLI Framework Decision

`feishu-bot-sdk` CLI uses Click as its sole command framework.

## Why Click

- Dynamic service/resource/method registration is cleaner than `argparse`
- Shell completion, hidden commands, and shared context are first-class
- The external command model matches `lark-cli`: `shortcut -> service -> raw api`

## Architecture

- Public root entry is `Click`
- Service commands are generated from synced `lark-cli` metadata snapshots
- High-value workflows live as `+shortcut` commands
- Special commands (webhook, ws, server, media) are native Click groups
- All legacy `argparse` infrastructure has been removed

## What stayed

- Existing SDK command handlers and runtime helpers are still reused
- Large-output controls remain: `--max-output-chars`, `--output-offset`, `--save-output`, `--full-output`

## Identity model

- Public identity flag is `--as user|bot|auto`
- Internal runtime still maps this to SDK auth modes (`user` / `tenant`)
- `default_as` replaces `default_identity` as the external profile field

## Metadata model

- Source of truth is the synced `lark-cli` registry schema
- Snapshot files live in `src/feishu_bot_sdk/cli/metadata/services/`
- Scope recommendation data is synced from `scope_priorities.json` and `scope_overrides.json`

## Command development rule

- All command families must be in the Click tree with `CliRunner` tests
- SDK command handlers (`commands/*.py`) are reused for execution logic
- `CLIContext.build_args()` creates `argparse.Namespace` objects consumed by handler functions
