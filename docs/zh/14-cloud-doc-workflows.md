# 14 云文档工作流速查

[English](../en/14-cloud-doc-workflows.md) | [返回中文索引](../README.md)

这一页只回答两个问题：

- 现在 SDK 和 CLI 到底能对云文档做什么
- 实际落地时，推荐怎么串这些命令

## 能力矩阵

| 场景 | SDK | CLI | 推荐入口 |
| --- | --- | --- | --- |
| 创建文档 | `DocxService.create_document` | `feishu docx create` | `docx` |
| 获取文档基础信息 | `DocxDocumentService.get_document` | `feishu docx get` | `docx` |
| 获取文档纯文本 | `DocxDocumentService.get_raw_content` | `feishu docx raw-content` | `docx` |
| 导出 Markdown / HTML | `DocContentService.get_content` | `feishu docx get-content` | `docs/v1/content` |
| Markdown / HTML 插入文档 | `DocxService.insert_content` | `feishu docx insert-content` | 官方 convert 流程 |
| 查看所有块 | `DocxDocumentService.list_blocks` | `feishu docx list-blocks` | `docx` |
| 查看某块内容 | `DocxBlockService.get_block` | `feishu docx get-block` | `docx` |
| 查看子块 / 后代块 | `DocxBlockService.list_children` | `feishu docx list-children` | `docx` |
| 插入若干块 | `DocxBlockService.create_children` | `feishu docx create-children` | `docx` |
| 一次插入嵌套块树 | `DocxBlockService.create_descendant` | `feishu docx create-descendant` | `docx` |
| 修改几个字 / 替换某块文本 | `DocxService.set_block_text` / `DocxBlockService.update_block` | `feishu docx set-block-text` / `feishu docx update-block` | `docx` |
| 修改文档标题 | `DocxService.set_title` | `feishu docx set-title` | Page Block |
| 批量改块 | `DocxBlockService.batch_update` | `feishu docx batch-update` | `docx` |
| 删除一段子块范围 | `DocxBlockService.delete_children_range` | `feishu docx delete-children-range` | `docx` |
| 替换图片块 | `DocxService.replace_image` | `feishu docx replace-image` | `docx_image` |
| 替换附件块 | `DocxService.replace_file` | `feishu docx replace-file` | `docx_file` |
| 查询文件元数据 | `DriveFileService.batch_query_metas` | `feishu drive meta` | `drive` |
| 查询文件统计 / 访问记录 | `DriveFileService.get_file_statistics` / `list_file_view_records` | `feishu drive stats` / `view-records` | `drive` |
| 复制 / 移动 / 删除 / 快捷方式 | `DriveFileService.copy_file` 等 | `feishu drive copy` 等 | `drive` |
| 文档版本管理 | `DriveFileService.create_version` 等 | `feishu drive version-*` | `drive` |

## 设计原则

- 写文档优先用 `insert-content`，不要自己解析 Markdown 再手拼块
- 精细编辑时，把“找块”与“改块”拆开
- 标题就是 Page Block 的文本，`document_id` 同时也是根块 `block_id`
- 图片和附件不直接塞 URL 或文件路径到块里，而是先上传素材，再 `replace_image` / `replace_file`

## 推荐 CLI 工作流

### 1. 创建文档并插入 Markdown

```bash
feishu docx create --title "日报" --folder-token fld_xxx --format json

feishu docx insert-content \
  --document-id doccn_xxx \
  --content-file ./report.md \
  --content-type markdown \
  --document-revision-id -1 \
  --format json
```

适用场景：

- 把 LLM 产出的 Markdown 直接落到云文档
- 内容里含标题、表格、图片时也照常处理

### 2. 导出 Markdown / HTML

```bash
feishu docx get-content \
  --doc-token doccn_xxx \
  --doc-type docx \
  --content-type markdown \
  --output ./report.md \
  --format json
```

适用场景：

- 把已有云文档回拉成 Markdown 做二次处理
- 做文档审查、归档、diff

### 3. 找到块，再改几个字

先看全量块：

```bash
feishu docx list-blocks --document-id doccn_xxx --all --format json
```

再替换某个块文本：

```bash
feishu docx set-block-text \
  --document-id doccn_xxx \
  --block-id blk_xxx \
  --text "这里是修改后的文本" \
  --document-revision-id -1 \
  --format json
```

如果你要保留复杂样式或直接调用官方子操作，就改用：

```bash
feishu docx update-block \
  --document-id doccn_xxx \
  --block-id blk_xxx \
  --operations-json '{"update_text":{"elements":[{"text_run":{"content":"新文本"}}]}}' \
  --document-revision-id -1 \
  --format json
```

### 4. 修改标题

```bash
feishu docx set-title \
  --document-id doccn_xxx \
  --text "新的文档标题" \
  --document-revision-id -1 \
  --format json
```

### 5. 删除一段内容

如果你已经知道父块以及子块区间：

```bash
feishu docx delete-children-range \
  --document-id doccn_xxx \
  --block-id blk_parent_xxx \
  --start-index 3 \
  --end-index 5 \
  --document-revision-id -1 \
  --format json
```

常见用法是先 `list-children` 再删：

```bash
feishu docx list-children \
  --document-id doccn_xxx \
  --block-id blk_parent_xxx \
  --with-descendants true \
  --all \
  --format json
```

### 6. 替换图片或附件

替换图片块：

```bash
feishu docx replace-image \
  --document-id doccn_xxx \
  --block-id blk_image_xxx \
  ./diagram.png \
  --document-revision-id -1 \
  --format json
```

替换附件块：

```bash
feishu docx replace-file \
  --document-id doccn_xxx \
  --block-id blk_file_xxx \
  ./contract.pdf \
  --document-revision-id -1 \
  --format json
```

### 7. 管理文件元数据和版本

查元数据：

```bash
feishu drive meta \
  --request-docs-json '[{"doc_token":"doccn_xxx","doc_type":"docx"}]' \
  --with-url true \
  --format json
```

创建版本：

```bash
feishu drive version-create doccn_xxx --name "发布版" --obj-type docx --format json
```

列出版本：

```bash
feishu drive version-list doccn_xxx --obj-type docx --page-size 50 --all --format json
```

## 推荐 SDK 工作流

```python
from feishu_bot_sdk import FeishuClient, FeishuConfig, DocxService

client = FeishuClient(FeishuConfig(app_id="cli_xxx", app_secret="xxx"))
docx = DocxService(client)

created = docx.create_document("周报")
document_id = created["document_id"]

docx.insert_content(document_id, "# 本周进展\n\n已完成 3 项任务。", content_type="markdown")
docx.set_title(document_id, "周报（已更新）")
docx.set_block_text(document_id, "blk_xxx", "局部替换后的文本")
```

## 选型建议

- 只有一整段 Markdown / HTML 要落地：`docx insert-content`
- 已经知道目标块，只想改几个字：`docx set-block-text`
- 需要复杂块级子操作：`docx update-block` / `batch-update`
- 需要版本、复制、移动、文件信息：`drive` 子命令
