# 邮箱功能详细参考

## 概述

邮箱模块提供三大类服务：
- **用户邮箱**：个人邮箱管理、邮件收发、文件夹、联系人、规则
- **邮件组**：邮件组管理、成员管理、权限管理
- **公共邮箱**：公共邮箱管理、成员管理

## 用户邮箱服务

### MailMailboxService - 邮箱管理

```python
from feishu_bot_sdk import MailMailboxService

mailbox = MailMailboxService(client)

# 列出邮箱别名
aliases = mailbox.list_aliases("me")

# 创建别名
mailbox.create_alias("me", "alias@example.com")

# 删除别名
mailbox.delete_alias("me", "alias@example.com")

# 永久删除回收站中的邮箱（可选转移邮件）
mailbox.delete_from_recycle_bin("old@example.com", transfer_mailbox="archive@example.com")
```

### MailMessageService - 邮件管理

```python
from feishu_bot_sdk import MailMessageService

message = MailMessageService(client)

# 列出邮件（分页）
result = message.list_messages("me", folder_id="INBOX", page_size=50)

# 迭代所有邮件（自动翻页）
for msg in message.iter_messages("me", folder_id="INBOX"):
    print(msg.get("subject"))

# 获取单封邮件
msg = message.get_message("me", "msg_xxx")

# 发送普通邮件
message.send_message("me", {
    "subject": "测试",
    "to": [{"mail_address": "user@example.com"}],
    "body_html": "<p>内容</p>",
    "body_plain_text": "内容"
})

# 发送 Markdown 邮件（推荐）
message.send_markdown(
    "me",
    subject="日报",
    to=["user@example.com"],  # 可直接传字符串列表
    cc=["cc@example.com"],
    markdown="# 日报\n\n![图表](./chart.png)\n\n完成情况...",
    base_dir="."  # 图片路径相对目录
)

# 获取附件下载链接
urls = message.get_attachment_download_urls("me", "msg_xxx", ["att_1", "att_2"])
```

### MailFolderService - 文件夹管理

```python
from feishu_bot_sdk import MailFolderService

folder = MailFolderService(client)

# 列出文件夹
folders = folder.list_folders("me")

# 迭代所有文件夹
for f in folder.iter_folders("me"):
    print(f.get("name"))

# 创建文件夹
folder.create_folder("me", "项目归档")

# 更新文件夹
folder.update_folder("me", "folder_xxx", "新名称")

# 删除文件夹
folder.delete_folder("me", "folder_xxx")
```

### MailContactService - 联系人管理

```python
from feishu_bot_sdk import MailContactService

contact = MailContactService(client)

# 列出联系人
contacts = contact.list_contacts("me", page_size=50)

# 迭代所有联系人
for c in contact.iter_contacts("me"):
    print(c.get("name"))

# 创建联系人
contact.create_contact("me", {
    "name": "张三",
    "email": "zhangsan@example.com"
})

# 更新联系人
contact.update_contact("me", "contact_xxx", {"name": "李四"})

# 删除联系人
contact.delete_contact("me", "contact_xxx")
```

### MailRuleService - 收信规则

```python
from feishu_bot_sdk import MailRuleService

rule = MailRuleService(client)

# 列出规则
rules = rule.list_rules("me")

# 迭代所有规则
for r in rule.iter_rules("me"):
    print(r.get("name"))

# 创建规则
rule.create_rule("me", {
    "name": "自动归档",
    "conditions": [...],
    "actions": [...]
})

# 更新规则
rule.update_rule("me", "rule_xxx", {"name": "新规则名"})

# 删除规则
rule.delete_rule("me", "rule_xxx")

# 重新排序规则
rule.reorder_rules("me", ["rule_1", "rule_2", "rule_3"])
```

### MailEventService - 事件订阅

```python
from feishu_bot_sdk import MailEventService

event = MailEventService(client)

# 获取订阅状态
subscription = event.get_subscription("me")

# 订阅事件
event.subscribe("me")

# 取消订阅
event.unsubscribe("me")
```

### MailAddressService - 地址状态查询

```python
from feishu_bot_sdk import MailAddressService

address = MailAddressService(client)

# 查询多个邮箱地址状态
status = address.query_status(["ops@example.com", "alerts@example.com"])
print(status.user_list)
```

## 邮件组服务

### MailGroupService - 邮件组管理

```python
from feishu_bot_sdk import MailGroupService

group = MailGroupService(client)

# 列出邮件组
groups = group.list_mailgroups(page_size=50)

# 迭代所有邮件组
for g in group.iter_mailgroups():
    print(g.get("name"))

# 获取邮件组详情
g = group.get_mailgroup("ops@example.com")

# 创建邮件组
created = group.create_mailgroup({
    "email": "ops@example.com",
    "name": "Ops Group",
    "description": "运维团队"
})

# 更新邮件组（部分更新）
group.update_mailgroup("ops@example.com", {"name": "新名称"})

# 替换邮件组（完整替换）
group.replace_mailgroup("ops@example.com", {
    "email": "ops@example.com",
    "name": "Ops Group",
    "description": "新描述"
})

# 删除邮件组
group.delete_mailgroup("ops@example.com")
```

### MailGroupAliasService - 邮件组别名

```python
from feishu_bot_sdk import MailGroupAliasService

alias = MailGroupAliasService(client)

# 列出别名
aliases = alias.list_aliases("ops@example.com")

# 创建别名
alias.create_alias("ops@example.com", "operations@example.com")

# 删除别名
alias.delete_alias("ops@example.com", "operations@example.com")
```

### MailGroupMemberService - 邮件组成员

```python
from feishu_bot_sdk import MailGroupMemberService

member = MailGroupMemberService(client)

# 列出成员
members = member.list_members("ops@example.com", user_id_type="open_id", page_size=50)

# 迭代所有成员
for m in member.iter_members("ops@example.com", user_id_type="open_id"):
    print(m.get("member_id"))

# 获取成员详情
m = member.get_member("ops@example.com", "ou_xxx", user_id_type="open_id")

# 添加成员
member.create_member("ops@example.com", "ou_xxx", user_id_type="open_id")

# 批量添加成员
member.batch_create_members("ops@example.com", ["ou_1", "ou_2"], user_id_type="open_id")

# 删除成员
member.delete_member("ops@example.com", "ou_xxx", user_id_type="open_id")

# 批量删除成员
member.batch_delete_members("ops@example.com", ["ou_1", "ou_2"], user_id_type="open_id")
```

### MailGroupPermissionMemberService - 权限成员

```python
from feishu_bot_sdk import MailGroupPermissionMemberService

perm = MailGroupPermissionMemberService(client)

# 列出权限成员
members = perm.list_permission_members("ops@example.com", user_id_type="open_id")

# 迭代所有权限成员
for m in perm.iter_permission_members("ops@example.com", user_id_type="open_id"):
    print(m.get("member_id"))

# 获取权限成员详情
m = perm.get_permission_member("ops@example.com", "ou_xxx", user_id_type="open_id")

# 添加权限成员
perm.create_permission_member("ops@example.com", "ou_xxx", user_id_type="open_id")

# 批量添加权限成员
perm.batch_create_permission_members("ops@example.com", ["ou_1", "ou_2"], user_id_type="open_id")

# 删除权限成员
perm.delete_permission_member("ops@example.com", "ou_xxx", user_id_type="open_id")

# 批量删除权限成员
perm.batch_delete_permission_members("ops@example.com", ["ou_1", "ou_2"], user_id_type="open_id")
```

### MailGroupManagerService - 邮件组管理员

```python
from feishu_bot_sdk import MailGroupManagerService

manager = MailGroupManagerService(client)

# 列出管理员
managers = manager.list_managers("ops@example.com", user_id_type="open_id")

# 迭代所有管理员
for m in manager.iter_managers("ops@example.com", user_id_type="open_id"):
    print(m.get("member_id"))

# 批量添加管理员
manager.batch_create_managers("ops@example.com", ["ou_1", "ou_2"], user_id_type="open_id")

# 批量删除管理员
manager.batch_delete_managers("ops@example.com", ["ou_1", "ou_2"], user_id_type="open_id")
```

## 公共邮箱服务

### PublicMailboxService - 公共邮箱管理

```python
from feishu_bot_sdk import PublicMailboxService

public = PublicMailboxService(client)

# 列出公共邮箱
mailboxes = public.list_public_mailboxes(page_size=50)

# 迭代所有公共邮箱
for mb in public.iter_public_mailboxes():
    print(mb.get("name"))

# 获取公共邮箱详情
mb = public.get_public_mailbox("support@example.com")

# 创建公共邮箱
created = public.create_public_mailbox({
    "email": "support@example.com",
    "name": "客户支持"
})

# 更新公共邮箱（部分更新）
public.update_public_mailbox("support@example.com", {"name": "新名称"})

# 替换公共邮箱（完整替换）
public.replace_public_mailbox("support@example.com", {
    "email": "support@example.com",
    "name": "客户支持"
})

# 移至回收站（可选指定接收地址）
public.remove_to_recycle_bin("support@example.com", to_mail_address="archive@example.com")

# 永久删除
public.delete_public_mailbox("support@example.com")
```

### PublicMailboxAliasService - 公共邮箱别名

```python
from feishu_bot_sdk import PublicMailboxAliasService

alias = PublicMailboxAliasService(client)

# 列出别名
aliases = alias.list_aliases("support@example.com")

# 创建别名
alias.create_alias("support@example.com", "help@example.com")

# 删除别名
alias.delete_alias("support@example.com", "help@example.com")
```

### PublicMailboxMemberService - 公共邮箱成员

```python
from feishu_bot_sdk import PublicMailboxMemberService

member = PublicMailboxMemberService(client)

# 列出成员
members = member.list_members("support@example.com", user_id_type="open_id")

# 迭代所有成员
for m in member.iter_members("support@example.com", user_id_type="open_id"):
    print(m.get("member_id"))

# 获取成员详情
m = member.get_member("support@example.com", "ou_xxx", user_id_type="open_id")

# 添加成员
member.create_member("support@example.com", "ou_xxx", user_id_type="open_id")

# 批量添加成员
member.batch_create_members("support@example.com", [
    {"user_id": "ou_1", "type": "USER"},
    {"user_id": "ou_2", "type": "USER"}
], user_id_type="open_id")

# 删除成员
member.delete_member("support@example.com", "ou_xxx", user_id_type="open_id")

# 批量删除成员
member.batch_delete_members("support@example.com", ["ou_1", "ou_2"], user_id_type="open_id")

# 清空所有成员
member.clear_members("support@example.com")
```

## Markdown 邮件渲染

### render_markdown_email 函数

```python
from feishu_bot_sdk import render_markdown_email

# 渲染 Markdown 为 HTML 邮件
rendered = render_markdown_email(
    markdown_content="# 日报\n\n![图表](./chart.png)\n\n完成情况...",
    base_dir=".",  # 图片路径相对目录
    css_style=None  # 可选自定义 CSS
)

# 返回 RenderedMarkdownEmail 对象
print(rendered.html)  # HTML 内容
print(rendered.plain_text)  # 纯文本版本
print(rendered.inline_images)  # 内联图片列表 [InlineImage(...), ...]

# InlineImage 对象
for img in rendered.inline_images:
    print(img.cid)  # Content-ID
    print(img.filename)  # 文件名
    print(img.content_type)  # MIME 类型
    print(img.data)  # base64 编码的图片数据
```

### 图片处理规则

1. **本地图片**：相对路径相对 `base_dir` 解析，自动读取并转 base64 内联
2. **远程图片**：HTTP/HTTPS URL 自动下载并转 base64 内联
3. **失败处理**：图片读取/下载失败时保留原始 URL，不阻断邮件发送
4. **CID 引用**：HTML 中图片 src 自动替换为 `cid:xxx` 格式

## CLI 命令参考

### 用户邮箱命令

```bash
# 邮箱别名
feishu mail mailbox alias list --user-mailbox-id me --format json
feishu mail mailbox alias create --user-mailbox-id me --email-alias alias@example.com
feishu mail mailbox alias delete --user-mailbox-id me --email-alias alias@example.com

# 永久删除邮箱
feishu mail mailbox delete-from-recycle-bin --user-mailbox-id old@example.com --transfer-mailbox archive@example.com

# 邮件管理
feishu mail message list --user-mailbox-id me --folder-id INBOX --all --format json
feishu mail message get --user-mailbox-id me --message-id msg_xxx --format json
feishu mail message send-markdown --user-mailbox-id me --to-email user@example.com --subject "日报" --markdown-file ./report.md

# 文件夹管理
feishu mail folder list --user-mailbox-id me --folder-type 2 --format json
feishu mail folder create --user-mailbox-id me --name "项目归档"
feishu mail folder delete --user-mailbox-id me --folder-id folder_xxx

# 联系人管理
feishu mail contact list --user-mailbox-id me --all --format json
feishu mail contact create --user-mailbox-id me --contact-json '{"name":"张三","email":"zhangsan@example.com"}'

# 收信规则
feishu mail rule list --user-mailbox-id me --all --format json
feishu mail rule create --user-mailbox-id me --rule-file ./rule.json

# 事件订阅
feishu mail event get-subscription --user-mailbox-id me
feishu mail event subscribe --user-mailbox-id me
feishu mail event unsubscribe --user-mailbox-id me

# 地址状态查询
feishu mail address query-status --email ops@example.com --email alerts@example.com --format json
```

### 邮件组命令

```bash
# 邮件组管理
feishu mail group list --all --format json
feishu mail group get --mailgroup-id ops@example.com --format json
feishu mail group create --mailgroup-json '{"email":"ops@example.com","name":"Ops Group"}'
feishu mail group update --mailgroup-id ops@example.com --mailgroup-json '{"name":"新名称"}'
feishu mail group delete --mailgroup-id ops@example.com

# 邮件组别名
feishu mail group alias list --mailgroup-id ops@example.com
feishu mail group alias create --mailgroup-id ops@example.com --email-alias operations@example.com

# 邮件组成员
feishu mail group member list --mailgroup-id ops@example.com --user-id-type open_id --all
feishu mail group member create --mailgroup-id ops@example.com --member-id ou_xxx --user-id-type open_id
feishu mail group member batch-create --mailgroup-id ops@example.com --member-ids-file ./members.json --user-id-type open_id
feishu mail group member batch-delete --mailgroup-id ops@example.com --member-ids-stdin --user-id-type open_id

# 权限成员
feishu mail group permission-member list --mailgroup-id ops@example.com --user-id-type open_id --all
feishu mail group permission-member batch-create --mailgroup-id ops@example.com --member-ids-file ./members.json --user-id-type open_id

# 管理员
feishu mail group manager list --mailgroup-id ops@example.com --user-id-type open_id --all
feishu mail group manager batch-create --mailgroup-id ops@example.com --member-ids-file ./managers.json --user-id-type open_id
```

### 公共邮箱命令

```bash
# 公共邮箱管理
feishu mail public-mailbox list --all --format json
feishu mail public-mailbox get --public-mailbox-id support@example.com --format json
feishu mail public-mailbox create --public-mailbox-json '{"email":"support@example.com","name":"客户支持"}'
feishu mail public-mailbox update --public-mailbox-id support@example.com --public-mailbox-json '{"name":"新名称"}'
feishu mail public-mailbox remove-to-recycle-bin --public-mailbox-id support@example.com --to-mail-address archive@example.com
feishu mail public-mailbox delete --public-mailbox-id support@example.com

# 公共邮箱别名
feishu mail public-mailbox alias list --public-mailbox-id support@example.com
feishu mail public-mailbox alias create --public-mailbox-id support@example.com --email-alias help@example.com

# 公共邮箱成员
feishu mail public-mailbox member list --public-mailbox-id support@example.com --user-id-type open_id --all
feishu mail public-mailbox member batch-create --public-mailbox-id support@example.com --items-file ./members.json --user-id-type open_id
feishu mail public-mailbox member clear --public-mailbox-id support@example.com
```

## 异步版本

所有服务都有对应的异步版本，在类名前加 `Async` 前缀：

```python
from feishu_bot_sdk import (
    AsyncMailMessageService,
    AsyncMailGroupService,
    AsyncPublicMailboxService,
)

# 使用方式
message = AsyncMailMessageService(client)
async for msg in message.iter_messages("me", folder_id="INBOX"):
    print(msg.get("subject"))

result = await message.send_markdown(
    "me",
    subject="日报",
    to=["user@example.com"],
    markdown="# 日报\n\n完成"
)
```

## 注意事项

1. `user_mailbox_id` 可以使用 `"me"` 表示当前用户邮箱
2. 批量操作建议使用 `batch_*` 方法，性能更好
3. Markdown 邮件发送会自动处理图片内联，无需手动处理附件
4. 邮件组和公共邮箱的 ID 通常是邮箱地址本身
5. 删除操作需要相应权限，建议先移至回收站再永久删除
6. 分页查询优先使用 `iter_*` 方法或 CLI 的 `--all` 参数
