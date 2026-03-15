# 05 Docx and Docs Content

[中文](../zh/05-docx-and-docs.md) | [Back to English Index](../README_EN.md)

## Covered Package

- `feishu_bot_sdk.docx` re-exports:
  `DocxService` / `AsyncDocxService`,
  `DocxDocumentService` / `AsyncDocxDocumentService`,
  `DocxBlockService` / `AsyncDocxBlockService`,
  `DocContentService` / `AsyncDocContentService`
- Internally the package is organized as `service` / `document` / `blocks` / `content`
- For normal usage, import from `feishu_bot_sdk.docx` and ignore the internal file layout

## Recommended Split

Treat Docx workflows as two separate concerns:

- Writing docs: prefer `DocxService.insert_content()`, which follows the official `convert -> create_descendant -> replace_image` flow
- Structured block editing: use `DocxBlockService`
- Exported content reads: use `DocContentService`
- Plain text reads: use `DocxDocumentService.get_raw_content()`

## Quick Example

```python
from feishu_bot_sdk import FeishuClient, FeishuConfig
from feishu_bot_sdk.docx import DocxService

client = FeishuClient(
    FeishuConfig(
        app_id="cli_xxx",
        app_secret="xxx",
        doc_url_prefix="https://your-tenant.feishu.cn/docx",
    )
)
docx = DocxService(client)

created = docx.create_document("Task Report", folder_token="fld_xxx")
document_id = created["document_id"]

docx.insert_content(
    document_id,
    "# Title\n\nBody text.\n\n![logo](https://example.com/logo.png)",
    content_type="markdown",
    document_revision_id=-1,
)
docx.set_title(document_id, "Task Report (Updated)")
docx.grant_edit_permission(document_id, "ou_xxx", "open_id")

print(created["url"] or document_id)
```

## `DocxService` (High-Level)

- Document creation: `create_document`
- Content insertion: `insert_content`, `append_markdown`
- Helper updates: `set_title`, `set_block_text`
- Asset replacement: `replace_image`, `replace_file`
- Content export: `get_content`
- Permission helper: `grant_edit_permission`

Key behavior:

- `insert_content` supports both `markdown` and `html`
- table blocks are sanitized before insert by removing read-only `merge_info`
- converted images are downloaded, uploaded as `docx_image` media, then patched with `replace_image`

## `DocxDocumentService` (Document Info)

- `create_document(title, folder_token=None)`
- `get_document(document_id)`
- `get_raw_content(document_id, lang=None)`
- `list_blocks(...)`
- `iter_blocks(...)`

## `DocxBlockService` (Block-Level Operations)

- Query: `get_block`, `list_children`, `iter_children`
- Create: `create_children`, `create_descendant`
- Update: `update_block`, `batch_update`
- Delete: `delete_children_range`
- Convert: `convert_content(content, content_type="markdown")`

Official request parameters are covered:

- write operations: `document_revision_id`, `client_token`
- read operations: `user_id_type`
- child listing: `with_descendants`

## `DocContentService` (`docs/v1/content`)

- `get_content(doc_token, doc_type="docx", content_type="markdown", lang=None)`
- `get_markdown(doc_token, doc_type="docx", lang=None)`

Use this for Markdown / HTML export workflows.

## Practical Guidance

- For Markdown / HTML insertion, do not build blocks manually; use `DocxService.insert_content`
- For partial edits, compose `list_children`, `update_block`, and `delete_children_range`
- For image or attachment replacement, create the empty block first, then call `replace_image` or `replace_file`
- For Markdown / HTML export, use `DocContentService` rather than write APIs
