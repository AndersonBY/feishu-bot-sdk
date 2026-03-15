# 15 邮箱（Mail）

[English](../en/15-mail.md) | [返回中文索引](../README.md)

## 覆盖模块

- `feishu_bot_sdk.mail` -> 用户邮箱、邮件组、公共邮箱三大类服务
- 根导出可直接使用：
  - 用户邮箱：`MailMailboxService`、`MailMessageService`、`MailFolderService`、`MailContactService`、`MailRuleService`、`MailEventService`、`MailAddressService`
  - 邮件组：`MailGroupService`、`MailGroupAliasService`、`MailGroupMemberService`、`MailGroupPermissionMemberService`、`MailGroupManagerService`
  - 公共邮箱：`PublicMailboxService`、`PublicMailboxAliasService`、`PublicMailboxMemberService`
- Markdown 邮件渲染辅助：
  - `render_markdown_email`
  - `prepare_html_inline_images`
  - `RenderedMarkdownEmail`、`InlineImage`

## 快速示例

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

rendered = render_markdown_email("# 日报\n\n![图表](./chart.png)\n\n![远程图](https://cdn.example.com/chart.png)", base_dir=".")
print(rendered.html[:120], len(rendered.inline_images))

message.send_markdown(
    "me",
    subject="日报",
    to=["user@example.com"],
    markdown="# 日报\n\n任务已完成",
)

group = MailGroupService(client)
created = group.create_mailgroup({"email": "ops@example.com", "name": "Ops Group"})
print(created.mailgroup_id)
```

## 用户邮箱 API

- 邮箱别名与回收站释放：
  - `list_aliases`、`create_alias`、`delete_alias`、`delete_from_recycle_bin`
- 用户邮件：
  - `list_messages`、`iter_messages`、`get_message`、`get_by_card`、`send_message`、`send_markdown`、`get_attachment_download_urls`
- 邮箱文件夹：
  - `list_folders`、`iter_folders`、`create_folder`、`update_folder`、`delete_folder`
- 邮箱联系人：
  - `list_contacts`、`iter_contacts`、`create_contact`、`update_contact`、`delete_contact`
- 收信规则：
  - `list_rules`、`iter_rules`、`create_rule`、`update_rule`、`delete_rule`、`reorder_rules`
- 事件订阅：
  - `get_subscription`、`subscribe`、`unsubscribe`
- 地址状态：
  - `query_status`

## 邮件组 API

- 邮件组管理：
  - `list_mailgroups`、`iter_mailgroups`、`get_mailgroup`、`create_mailgroup`、`update_mailgroup`、`replace_mailgroup`、`delete_mailgroup`
- 邮件组别名：
  - `list_aliases`、`create_alias`、`delete_alias`
- 邮件组成员：
  - `list_members`、`iter_members`、`get_member`、`create_member`、`batch_create_members`、`delete_member`、`batch_delete_members`
- 邮件组权限成员：
  - `list_permission_members`、`iter_permission_members`、`get_permission_member`、`create_permission_member`、`batch_create_permission_members`、`delete_permission_member`、`batch_delete_permission_members`
- 邮件组管理员：
  - `list_managers`、`iter_managers`、`batch_create_managers`、`batch_delete_managers`

## 公共邮箱 API

- 公共邮箱管理：
  - `list_public_mailboxes`、`iter_public_mailboxes`、`get_public_mailbox`、`create_public_mailbox`、`update_public_mailbox`、`replace_public_mailbox`、`remove_to_recycle_bin`、`delete_public_mailbox`
- 公共邮箱别名：
  - `list_aliases`、`create_alias`、`delete_alias`
- 公共邮箱成员：
  - `list_members`、`iter_members`、`get_member`、`create_member`、`batch_create_members`、`delete_member`、`batch_delete_members`、`clear_members`

## CLI 示例

```bash
# 查询邮箱地址状态
feishu mail address query-status --email ops@example.com --email alerts@example.com --format json

# 列出收件箱邮件（自动翻页）
feishu mail message list --user-mailbox-id me --folder-id INBOX --all --format json

# 从 Markdown 文件渲染 HTML 邮件并发送
feishu mail message send-markdown --user-mailbox-id me --to-email user@example.com --subject "日报" --markdown-file ./report.md --format json

# 创建用户邮箱别名
feishu mail mailbox alias create --user-mailbox-id me --email-alias alias@example.com --format json

# 永久删除回收站中的用户邮箱，并转移邮件
feishu mail mailbox delete-from-recycle-bin --user-mailbox-id old@example.com --transfer-mailbox archive@example.com --format json

# 按类型过滤邮箱文件夹
feishu mail folder list --user-mailbox-id me --folder-type 2 --format json

# 创建邮件组
feishu mail group create --mailgroup-json '{"email":"ops@example.com","name":"Ops Group"}' --format json

# 批量删除邮件组成员（从 stdin 读取 member_id 列表）
echo '["ou_1","ou_2"]' | feishu mail group member batch-delete --mailgroup-id ops@example.com --member-ids-stdin --user-id-type open_id --format json

# 将公共邮箱移至回收站并指定接收地址
feishu mail public-mailbox remove-to-recycle-bin --public-mailbox-id support@example.com --to-mail-address archive@example.com --format json

# 批量添加公共邮箱成员
feishu mail public-mailbox member batch-create --public-mailbox-id support@example.com --items-file ./members.json --format json
```

## 注意事项

- `mailbox alias create`、`group alias create`、`public-mailbox alias create` 底层请求字段都是 `email_alias`。CLI 已提供直接参数 `--email-alias`。
- `mail message send-markdown` 会自动生成 `body_html` 和 `body_plain_text`，并把 Markdown 里的本地图片路径或远程图片 URL 抓取后转成内联 CID 附件。
- `mail message send-markdown` 可直接用 `--to-email` / `--cc-email` / `--bcc-email`，也支持 `--to-json` / `--cc-json` / `--bcc-json` 传完整收件人对象（字段名用 `mail_address`）。
- `mail message send-markdown` 若使用 `--markdown-file`，相对图片路径默认相对该 Markdown 文件目录解析；也可手动用 `--base-dir` 覆盖。
- SDK `MailMessageService.send_markdown()` 与 `AsyncMailMessageService.send_markdown()` 同样支持直接传字符串收件人列表，内部会规范化成 `mail_address` 对象。
- `render_markdown_email()` 可单独使用，适合先预览 HTML 或把渲染结果接到你自己的邮件发送链路中；远程图片抓取失败时会保留原始 URL，不会阻断整封邮件发送。
- `mail message list`、`mail contact list`、`mail rule list`、`mail group list`、`mail group member list`、`mail group permission-member list`、`mail group manager list`、`mail public-mailbox list`、`mail public-mailbox member list` 支持 `--all`。
- `mail folder list` 官方不是分页接口，CLI 不提供 `--all`，而是提供 `--folder-type 1|2` 过滤系统文件夹/用户文件夹。
- 永久删除用户邮箱时可用 `--transfer-mailbox` 转移邮件；移除公共邮箱到回收站时可用 `--to-mail-address` 指定接收地址。
- 批量命令优先使用 `--*-file` 或 `--*-stdin`，这样 Agent 更容易通过结构化 JSON 数组稳定调用。

## 异步版

- 所有服务都有 `Async*` 对应版本，方法名与同步版保持一致。
- 分页迭代方法改为 `async for`，普通调用改为 `await`。
