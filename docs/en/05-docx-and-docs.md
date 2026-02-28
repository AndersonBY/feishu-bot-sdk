# 05 Docx and Docs Content

[中文](../zh/05-docx-and-docs.md) | [Back to English Index](../README_EN.md)

## Covered Modules

- `feishu_bot_sdk.docx` -> `DocxService` / `AsyncDocxService`
- `feishu_bot_sdk.docx_document` -> `DocxDocumentService` / `AsyncDocxDocumentService`
- `feishu_bot_sdk.docx_blocks` -> `DocxBlockService` / `AsyncDocxBlockService`
- `feishu_bot_sdk.docs_content` -> `DocContentService` / `AsyncDocContentService`

## Quick Example

```python
from feishu_bot_sdk import FeishuClient, FeishuConfig, DocxService

client = FeishuClient(
    FeishuConfig(
        app_id="cli_xxx",
        app_secret="xxx",
        doc_url_prefix="https://your-tenant.feishu.cn/docx",
    )
)
docx = DocxService(client)

doc_id, doc_url = docx.create_document("Task Report")
docx.append_markdown(doc_id, "# Title\n\nBody text.")
docx.grant_edit_permission(doc_id, "ou_xxx", "open_id")
print(doc_url or doc_id)
```

## `DocxService` (High-Level)

- `create_document(title)`
- `append_markdown(document_id, markdown_text)`
- `grant_edit_permission(document_id, member_id, member_id_type="open_id")`

Use this for quick Markdown-to-doc workflows.

## `DocxDocumentService` (Document and Block Listing)

- Document APIs: `create_document`, `get_document`, `get_raw_content`
- Block listing: `list_blocks`, `iter_blocks`

## `DocxBlockService` (Block-Level Operations)

- Query: `get_block`, `list_children`, `iter_children`
- Create: `create_children`, `create_descendant`
- Update: `update_block`, `batch_update`
- Delete: `delete_children_range`
- Convert: `convert_content` (markdown/html to doc blocks)

## `DocContentService` (`docs/v1/content`)

- `get_content(doc_token, doc_type="docx", content_type="markdown", lang=None)`
- `get_markdown(doc_token, doc_type="docx", lang=None)`

Use this when you need exported content text.

## Practical Guidance

- For report generation, start with `DocxService.append_markdown`.
- For structured edits, switch to `DocxBlockService`.
- For downstream text processing, use `DocContentService.get_markdown`.
