# 14 Cloud Doc Workflows

[中文](../zh/14-cloud-doc-workflows.md) | [Back to English Index](../README_EN.md)

This page answers two practical questions:

- what the SDK and CLI can now do for Feishu cloud docs
- which command sequences are the recommended workflows

## Capability Matrix

| Scenario | SDK | CLI | Recommended entry |
| --- | --- | --- | --- |
| Create document | `DocxService.create_document` | `feishu docx create` | `docx` |
| Get document metadata | `DocxDocumentService.get_document` | `feishu docx get` | `docx` |
| Get plain text content | `DocxDocumentService.get_raw_content` | `feishu docx raw-content` | `docx` |
| Export Markdown / HTML | `DocContentService.get_content` | `feishu docx get-content` | `docs/v1/content` |
| Insert Markdown / HTML into doc | `DocxService.insert_content` | `feishu docx insert-content` | official convert flow |
| List all blocks | `DocxDocumentService.list_blocks` | `feishu docx list-blocks` | `docx` |
| Read one block | `DocxBlockService.get_block` | `feishu docx get-block` | `docx` |
| Read children / descendants | `DocxBlockService.list_children` | `feishu docx list-children` | `docx` |
| Insert direct child blocks | `DocxBlockService.create_children` | `feishu docx create-children` | `docx` |
| Insert nested block tree | `DocxBlockService.create_descendant` | `feishu docx create-descendant` | `docx` |
| Change a few characters / replace block text | `DocxService.set_block_text` / `DocxBlockService.update_block` | `feishu docx set-block-text` / `feishu docx update-block` | `docx` |
| Update document title | `DocxService.set_title` | `feishu docx set-title` | Page Block |
| Batch block updates | `DocxBlockService.batch_update` | `feishu docx batch-update` | `docx` |
| Delete a child block range | `DocxBlockService.delete_children_range` | `feishu docx delete-children-range` | `docx` |
| Replace image block | `DocxService.replace_image` | `feishu docx replace-image` | `docx_image` |
| Replace file block | `DocxService.replace_file` | `feishu docx replace-file` | `docx_file` |
| Query file metadata | `DriveFileService.batch_query_metas` | `feishu drive meta` | `drive` |
| Query stats / view records | `DriveFileService.get_file_statistics` / `list_file_view_records` | `feishu drive stats` / `view-records` | `drive` |
| Copy / move / delete / shortcut | `DriveFileService.copy_file` etc. | `feishu drive copy` etc. | `drive` |
| Document version management | `DriveFileService.create_version` etc. | `feishu drive version-*` | `drive` |

## Design Rules

- For document writes, prefer `insert-content`; do not hand-build Markdown block trees
- For precise edits, separate "locate blocks" from "mutate blocks"
- The title lives on the Page Block, and `document_id` is also the root `block_id`
- Images and attachments are not written as raw URLs or local paths into blocks; upload media first, then `replace_image` or `replace_file`

## Recommended CLI Workflows

### 1. Create a document and insert Markdown

```bash
feishu docx create --title "Daily Report" --folder-token fld_xxx --format json

feishu docx insert-content \
  --document-id doccn_xxx \
  --content-file ./report.md \
  --content-type markdown \
  --document-revision-id -1 \
  --format json
```

Use this when:

- you want to land LLM-generated Markdown into a doc
- the content includes headings, tables, or images

### 2. Export Markdown / HTML

```bash
feishu docx get-content \
  --doc-token doccn_xxx \
  --doc-type docx \
  --content-type markdown \
  --output ./report.md \
  --format json
```

Use this when:

- you want to pull an existing doc back into Markdown
- you need review, archive, or diff workflows

### 3. Locate a block, then change a few words

List all blocks first:

```bash
feishu docx list-blocks --document-id doccn_xxx --all --format json
```

Then replace one block's text:

```bash
feishu docx set-block-text \
  --document-id doccn_xxx \
  --block-id blk_xxx \
  --text "Updated text here" \
  --document-revision-id -1 \
  --format json
```

If you need lower-level official operations:

```bash
feishu docx update-block \
  --document-id doccn_xxx \
  --block-id blk_xxx \
  --operations-json '{"update_text":{"elements":[{"text_run":{"content":"New text"}}]}}' \
  --document-revision-id -1 \
  --format json
```

### 4. Update the title

```bash
feishu docx set-title \
  --document-id doccn_xxx \
  --text "New Title" \
  --document-revision-id -1 \
  --format json
```

### 5. Delete a content range

If you already know the parent block and child indices:

```bash
feishu docx delete-children-range \
  --document-id doccn_xxx \
  --block-id blk_parent_xxx \
  --start-index 3 \
  --end-index 5 \
  --document-revision-id -1 \
  --format json
```

Common pattern: inspect first, then delete:

```bash
feishu docx list-children \
  --document-id doccn_xxx \
  --block-id blk_parent_xxx \
  --with-descendants true \
  --all \
  --format json
```

### 6. Replace an image or attachment

Replace an image block:

```bash
feishu docx replace-image \
  --document-id doccn_xxx \
  --block-id blk_image_xxx \
  ./diagram.png \
  --document-revision-id -1 \
  --format json
```

Replace a file block:

```bash
feishu docx replace-file \
  --document-id doccn_xxx \
  --block-id blk_file_xxx \
  ./contract.pdf \
  --document-revision-id -1 \
  --format json
```

### 7. Manage metadata and versions

Query metadata:

```bash
feishu drive meta \
  --request-docs-json '[{"doc_token":"doccn_xxx","doc_type":"docx"}]' \
  --with-url true \
  --format json
```

Create a version:

```bash
feishu drive version-create doccn_xxx --name "Release" --obj-type docx --format json
```

List versions:

```bash
feishu drive version-list doccn_xxx --obj-type docx --page-size 50 --all --format json
```

## Recommended SDK Workflow

```python
from feishu_bot_sdk import FeishuClient, FeishuConfig, DocxService

client = FeishuClient(FeishuConfig(app_id="cli_xxx", app_secret="xxx"))
docx = DocxService(client)

created = docx.create_document("Weekly Report")
document_id = created["document_id"]

docx.insert_content(document_id, "# This Week\n\nCompleted 3 tasks.", content_type="markdown")
docx.set_title(document_id, "Weekly Report (Updated)")
docx.set_block_text(document_id, "blk_xxx", "Partially replaced text")
```

## Selection Guide

- One full Markdown / HTML payload to land: `docx insert-content`
- You already know the block and only need a small text edit: `docx set-block-text`
- You need low-level block operations: `docx update-block` / `batch-update`
- You need versions, copy, move, or file metadata: `drive` subcommands
