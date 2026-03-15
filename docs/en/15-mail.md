# 15 Mail

[中文版](../zh/15-mail.md) | [Back to English Index](../README_EN.md)

## Module Coverage

- `feishu_bot_sdk.mail` covers user mailboxes, mail groups, and public mailboxes
- Direct root exports include:
  - User mailbox: `MailMailboxService`, `MailMessageService`, `MailFolderService`, `MailContactService`, `MailRuleService`, `MailEventService`, `MailAddressService`
  - Mail group: `MailGroupService`, `MailGroupAliasService`, `MailGroupMemberService`, `MailGroupPermissionMemberService`, `MailGroupManagerService`
  - Public mailbox: `PublicMailboxService`, `PublicMailboxAliasService`, `PublicMailboxMemberService`
- Markdown mail rendering helpers:
  - `render_markdown_email`
  - `prepare_html_inline_images`
  - `RenderedMarkdownEmail`, `InlineImage`

## Quick Example

```python
from feishu_bot_sdk import (
    FeishuClient,
    FeishuConfig,
    MailAddressService,
    MailMessageService,
    MailGroupService,
    render_markdown_email,
)

client = FeishuClient(FeishuConfig(app_id="cli_xxx", app_secret="xxx"))

address = MailAddressService(client)
status = address.query_status(["ops@example.com", "alerts@example.com"])
print(status.user_list)

message = MailMessageService(client)
for item in message.iter_messages("me", folder_id="INBOX", page_size=50):
    print(item.get("subject"))

rendered = render_markdown_email("# Daily Report\n\n![Chart](./chart.png)\n\n![Remote](https://cdn.example.com/chart.png)", base_dir=".")
print(rendered.html[:120], len(rendered.inline_images))

message.send_markdown(
    "me",
    subject="Daily Report",
    to=["user@example.com"],
    markdown="# Daily Report\n\nTask completed",
)

group = MailGroupService(client)
created = group.create_mailgroup({"email": "ops@example.com", "name": "Ops Group"})
print(created.mailgroup_id)
```

## User Mailbox APIs

- Mailbox aliases and recycle-bin release:
  - `list_aliases`, `create_alias`, `delete_alias`, `delete_from_recycle_bin`
- User messages:
  - `list_messages`, `iter_messages`, `get_message`, `get_by_card`, `send_message`, `send_markdown`, `get_attachment_download_urls`
- Mailbox folders:
  - `list_folders`, `iter_folders`, `create_folder`, `update_folder`, `delete_folder`
- Mail contacts:
  - `list_contacts`, `iter_contacts`, `create_contact`, `update_contact`, `delete_contact`
- Inbox rules:
  - `list_rules`, `iter_rules`, `create_rule`, `update_rule`, `delete_rule`, `reorder_rules`
- Event subscription:
  - `get_subscription`, `subscribe`, `unsubscribe`
- Address status:
  - `query_status`

## Mail Group APIs

- Mail group management:
  - `list_mailgroups`, `iter_mailgroups`, `get_mailgroup`, `create_mailgroup`, `update_mailgroup`, `replace_mailgroup`, `delete_mailgroup`
- Mail group aliases:
  - `list_aliases`, `create_alias`, `delete_alias`
- Mail group members:
  - `list_members`, `iter_members`, `get_member`, `create_member`, `batch_create_members`, `delete_member`, `batch_delete_members`
- Mail group permission members:
  - `list_permission_members`, `iter_permission_members`, `get_permission_member`, `create_permission_member`, `batch_create_permission_members`, `delete_permission_member`, `batch_delete_permission_members`
- Mail group managers:
  - `list_managers`, `iter_managers`, `batch_create_managers`, `batch_delete_managers`

## Public Mailbox APIs

- Public mailbox management:
  - `list_public_mailboxes`, `iter_public_mailboxes`, `get_public_mailbox`, `create_public_mailbox`, `update_public_mailbox`, `replace_public_mailbox`, `remove_to_recycle_bin`, `delete_public_mailbox`
- Public mailbox aliases:
  - `list_aliases`, `create_alias`, `delete_alias`
- Public mailbox members:
  - `list_members`, `iter_members`, `get_member`, `create_member`, `batch_create_members`, `delete_member`, `batch_delete_members`, `clear_members`

## CLI Examples

```bash
# query mailbox address status
feishu mail address query-status --email ops@example.com --email alerts@example.com --format json

# list inbox messages with auto-pagination
feishu mail message list --user-mailbox-id me --folder-id INBOX --all --format json

# render a Markdown file into HTML email and send it
feishu mail message send-markdown --user-mailbox-id me --to-email user@example.com --subject "Daily Report" --markdown-file ./report.md --format json

# create a user mailbox alias
feishu mail mailbox alias create --user-mailbox-id me --email-alias alias@example.com --format json

# permanently delete a mailbox from recycle bin and transfer mail
feishu mail mailbox delete-from-recycle-bin --user-mailbox-id old@example.com --transfer-mailbox archive@example.com --format json

# filter mailbox folders by type
feishu mail folder list --user-mailbox-id me --folder-type 2 --format json

# create a mail group
feishu mail group create --mailgroup-json '{"email":"ops@example.com","name":"Ops Group"}' --format json

# batch delete mail group members from stdin
echo '["ou_1","ou_2"]' | feishu mail group member batch-delete --mailgroup-id ops@example.com --member-ids-stdin --user-id-type open_id --format json

# move a public mailbox to recycle bin with transfer target
feishu mail public-mailbox remove-to-recycle-bin --public-mailbox-id support@example.com --to-mail-address archive@example.com --format json

# batch add public mailbox members
feishu mail public-mailbox member batch-create --public-mailbox-id support@example.com --items-file ./members.json --format json
```

## Notes

- `mailbox alias create`, `group alias create`, and `public-mailbox alias create` all use the request field `email_alias`. The CLI exposes a direct `--email-alias` flag for this.
- `mail message send-markdown` automatically builds both `body_html` and `body_plain_text`, and converts local image paths or remote image URLs in Markdown into inline CID attachments.
- `mail message send-markdown` supports direct recipient flags (`--to-email`, `--cc-email`, `--bcc-email`) and JSON array inputs (`--to-json`, `--cc-json`, `--bcc-json`) when you need full recipient objects with `mail_address`.
- When `--markdown-file` is used, relative image paths are resolved from that file's directory by default. Use `--base-dir` to override.
- `MailMessageService.send_markdown()` and `AsyncMailMessageService.send_markdown()` accept plain string recipient lists and normalize them into `mail_address` objects for the send-mail API.
- `render_markdown_email()` is also useful standalone when you want to preview the generated HTML or reuse the rendered output in your own mail pipeline. If a remote image cannot be fetched, the original URL is kept instead of failing the whole render/send flow.
- `mail message list`, `mail contact list`, `mail rule list`, `mail group list`, `mail group member list`, `mail group permission-member list`, `mail group manager list`, `mail public-mailbox list`, and `mail public-mailbox member list` support `--all`.
- `mail folder list` is not a paged API in the official docs, so the CLI exposes `--folder-type 1|2` instead of `--all`.
- Use `--transfer-mailbox` when permanently deleting a user mailbox, and `--to-mail-address` when moving a public mailbox to recycle bin with a transfer target.
- For batch commands, prefer `--*-file` or `--*-stdin` so Agents can provide structured JSON arrays reliably.

## Async Version

- Every sync service has a matching `Async*` variant with the same method names.
- Use `await` for normal calls and `async for` for iterator-style methods.
