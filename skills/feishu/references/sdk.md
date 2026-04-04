# Python SDK Reference

## Configuration

```python
from feishu_bot_sdk import FeishuConfig, FeishuClient

config = FeishuConfig(
    app_id="cli_xxx",
    app_secret="xxx",
    base_url="https://open.feishu.cn/open-apis",  # default
    tenant_access_token=None,          # optional, skip auto-auth
    doc_url_prefix="https://tenant.feishu.cn/docx",  # for doc URLs
    doc_folder_token="fldcnxxx",       # folder for new docs
    timeout_seconds=30.0,
    rate_limit_enabled=True,           # adaptive rate limiting
    rate_limit_base_qps=5.0,
)
```

Environment variables: `FEISHU_APP_ID`, `FEISHU_APP_SECRET` (also `APP_ID`, `APP_SECRET`).

## MessageService

```python
from feishu_bot_sdk import MessageService

msg = MessageService(client)

# Send
msg.send_text(receive_id_type="open_id", receive_id="ou_xxx", text="hello")
msg.send_markdown(receive_id_type="open_id", receive_id="ou_xxx", markdown="# Title")
msg.send_image(receive_id_type="open_id", receive_id="ou_xxx", image_key="img_xxx")
msg.send_interactive(receive_id_type="open_id", receive_id="ou_xxx", interactive={...})
msg.send_post(receive_id_type="open_id", receive_id="ou_xxx", post={...})
msg.send_file(receive_id_type="open_id", receive_id="ou_xxx", file_key="file_xxx")
msg.send_audio(receive_id_type="open_id", receive_id="ou_xxx", file_key="file_xxx")
msg.send_media(receive_id_type="open_id", receive_id="ou_xxx", file_key="f", image_key="i")
msg.send_share_chat(receive_id_type="open_id", receive_id="ou_xxx", chat_id="oc_xxx")
msg.send_share_user(receive_id_type="open_id", receive_id="ou_xxx", user_open_id="ou_xxx")
msg.send_sticker(receive_id_type="open_id", receive_id="ou_xxx", sticker_key="sticker_xxx")

# Reply
msg.reply_text(message_id="om_xxx", text="reply")
msg.reply_markdown(message_id="om_xxx", markdown="# Reply")
msg.reply(message_id="om_xxx", msg_type="text", content={"text": "reply"})

# Operations
msg.get(message_id="om_xxx")
msg.recall(message_id="om_xxx")
msg.edit(message_id="om_xxx", msg_type="text", content={"text": "edited"})
msg.forward(message_id="om_xxx", receive_id_type="open_id", receive_id="ou_xxx")
msg.merge_forward(message_id_list=["om_1", "om_2"], receive_id_type="open_id", receive_id="ou_xxx")
msg.list_history(receive_id_type="open_id", receive_id="ou_xxx")
msg.query_read_users(message_id="om_xxx")

# Reactions / Pins / Urgent
msg.add_reaction(message_id="om_xxx", emoji_type="SMILE")
msg.list_reactions(message_id="om_xxx")
msg.delete_reaction(message_id="om_xxx", reaction_id="reaction_xxx")
msg.pin_message(message_id="om_xxx")
msg.unpin_message(message_id="om_xxx")
msg.send_urgent_app(message_id="om_xxx", user_id_list=["ou_xxx"], user_id_type="open_id")
msg.send_batch_message(msg_type="text", content={"text": "batch"}, open_ids=["ou_1", "ou_2"])
```

## MediaService

```python
from feishu_bot_sdk import MediaService

media = MediaService(client)

media.upload_image("photo.png", image_type="message")  # -> {"image_key": "img_xxx"}
media.upload_file("doc.pdf", file_type="pdf", file_name="MyDoc")  # -> {"file_key": "file_xxx"}
media.download_image(image_key="img_xxx")  # -> bytes
media.download_file(file_key="file_xxx")  # -> bytes
media.download_message_resource(message_id="om_xxx", file_key="file_xxx", resource_type="file")
```

## BitableService

```python
from feishu_bot_sdk import BitableService

bt = BitableService(client)

# Create from CSV
app_token, app_url = bt.create_from_csv("data.csv", "App Name", "Sheet1")
bt.grant_edit_permission(app_token, member_id="ou_xxx")

# Table/Record CRUD
bt.create_table(app_token, {"name": "Table2", "fields": [...]})
bt.list_tables(app_token)
bt.create_record(app_token, "tblXXX", {"Name": "Alice", "Score": 95})
bt.update_record(app_token, "tblXXX", "recXXX", {"Score": 100})
bt.delete_record(app_token, "tblXXX", "recXXX")
bt.get_record(app_token, "tblXXX", "recXXX")
bt.list_records(app_token, "tblXXX", page_size=100)

# Pagination iterator
for item in bt.iter_records(app_token, "tblXXX", page_size=50):
    print(item["record_id"])

# Batch operations
bt.batch_create_records(app_token, "tblXXX", [{"Name": "A"}, {"Name": "B"}])
bt.batch_update_records(app_token, "tblXXX", [{"record_id": "recXXX", "fields": {"Name": "Updated"}}])
```

## DocxService

```python
from feishu_bot_sdk import DocxService

docx = DocxService(client)

doc_id, doc_url = docx.create_document("Title")
docx.append_markdown(doc_id, "# Heading\n\nContent")
docx.grant_edit_permission(doc_id, member_id="ou_xxx")
docx.grant_full_access_permission(doc_id, member_id="ou_xxx")
docx.revoke_permission(doc_id, member_id="ou_xxx")
```

## DriveFileService / DrivePermissionService

```python
from feishu_bot_sdk import DriveFileService, DrivePermissionService

drive = DriveFileService(client)
perm = DrivePermissionService(client)

drive.upload_file("report.pdf", parent_type="explorer", parent_node="fldXXX")
drive.create_import_task({...})
drive.get_import_task("ticket_xxx")
drive.create_export_task({...})
drive.get_export_task("ticket_xxx")

perm.add_member(token, resource_type="bitable", member_id="ou_xxx", perm="edit")
perm.list_members(token, resource_type="bitable")
perm.set_public_access(token, resource_type="bitable", public_perm="anyone_readable")
```

## TaskService

```python
from feishu_bot_sdk import TaskService

task = TaskService(client)

# Task CRUD
task.create_task({"summary": "Review PR"}, user_id_type="open_id")
task.get_task("task_xxx", user_id_type="open_id")
task.update_task("task_xxx", {"completed_at": "0"}, update_fields=["completed_at"], user_id_type="open_id")
task.delete_task("task_xxx")

# Members / reminders / comments
task.add_task_members("task_xxx", [{"id": "ou_xxx", "role": "assignee", "type": "user"}], user_id_type="open_id")
task.remove_task_members("task_xxx", [{"id": "ou_xxx", "role": "follower", "type": "user"}], user_id_type="open_id")
task.add_task_reminders("task_xxx", [{"relative_fire_minute": 60}], user_id_type="open_id")
task.remove_task_reminders("task_xxx", ["rid_xxx"], user_id_type="open_id")
task.create_comment("task_xxx", "Please verify again")
```

## WikiService / DocContentService

```python
from feishu_bot_sdk import WikiService, DocContentService

wiki = WikiService(client)
wiki.list_spaces(page_size=10)
wiki.get_space(space_id="spaceXXX")
wiki.search_nodes("project plan", page_size=10)
wiki.get_node(token="wikiXXX")
wiki.list_nodes(space_id="spaceXXX")
for space in wiki.iter_spaces(page_size=20):
    print(space["space_id"])

doc_content = DocContentService(client)
doc_content.get_doc_content(doc_token="docXXX", doc_type="docx")  # -> markdown
```

## CardKitService

CardKit 卡片实体 API，用于创建卡片实体、流式更新内容、控制 streaming_mode。

```python
from feishu_bot_sdk import CardKitService, MessageContent

cardkit = CardKitService(client)

# 1. Create card entity (card JSON must have "schema": "2.0" and use body.elements)
card_json = {
    "schema": "2.0",
    "config": {"wide_screen_mode": True, "streaming_mode": True},
    "header": {"title": {"tag": "plain_text", "content": "Title"}, "template": "blue"},
    "body": {"elements": [{"tag": "markdown", "element_id": "el_1", "content": ""}]},
}
resp = cardkit.create(card=card_json)  # -> CardKitCreateResponse (card_id, ok, code, msg)

# 2. Send card as interactive message
content = MessageContent.interactive_card(resp.card_id)
msg.send(receive_id_type="open_id", receive_id="ou_xxx", msg_type="interactive", content=content)

# 3. Stream content (打字机效果, sequence 必须严格递增)
cardkit.set_element_content(resp.card_id, element_id="el_1", content="Hello", sequence=1)
cardkit.set_element_content(resp.card_id, element_id="el_1", content="Hello, world!", sequence=2)

# 4. Toggle streaming mode
cardkit.set_streaming_mode(resp.card_id, enabled=False, sequence=3)

# 5. Full card update
cardkit.update(resp.card_id, card=final_card_json, sequence=4)

# 6. Update card settings (generic)
cardkit.set_settings(resp.card_id, settings={"config": {"streaming_mode": True}}, sequence=5)
```

Typed responses:
- `CardKitCreateResponse`: `card_id`, `ok`, `code`, `msg`, `raw`
- `CardKitResponse`: `ok`, `code`, `msg`, `raw`

## CardCallbackResponse

card.action.trigger 回调响应构造 helper：

```python
from feishu_bot_sdk import CardCallbackResponse

# Toast (即时响应)
CardCallbackResponse.toast("Done!", type="success")
# -> {"toast": {"type": "success", "content": "Done!"}}

# Return updated card inline
CardCallbackResponse.card({"elements": [...]})
# -> {"card": {"elements": [...]}}

# Arbitrary inline payload
CardCallbackResponse.inline(toast={"type": "info"}, card={...})
```

## MessageContent Builder

```python
from feishu_bot_sdk import MessageContent

# Markdown post
post = MessageContent.post_locale(
    locale="zh_cn", title="Report",
    content=[[MessageContent.post_md("# Title\n\nBody")]]
)

# Simple content
MessageContent.image(image_key="img_xxx")
MessageContent.share_chat(chat_id="oc_xxx")
MessageContent.share_user(user_open_id="ou_xxx")
```

## Async Usage

All services have `Async*` counterparts:

```python
from feishu_bot_sdk import AsyncFeishuClient, AsyncMessageService, FeishuConfig

config = FeishuConfig(app_id="cli_xxx", app_secret="xxx")
client = AsyncFeishuClient(config)
msg = AsyncMessageService(client)

await msg.send_text(receive_id_type="open_id", receive_id="ou_xxx", text="async hello")
await client.aclose()
```

## Idempotency

```python
from feishu_bot_sdk import build_idempotency_key

key = build_idempotency_key(event_id="evt_xxx", handler_name="on_message")
msg.send_text(..., uuid=key)
```

## Exceptions

```python
from feishu_bot_sdk import SDKError, ConfigurationError, HTTPRequestError, FeishuError

# SDKError (base)
#   ConfigurationError - missing/invalid config
#   HTTPRequestError   - HTTP failures (has status_code, response_text, response_headers)
#   FeishuError        - API business errors
```
