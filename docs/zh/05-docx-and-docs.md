# 05 云文档（Docx/Docs Content）

[English](../en/05-docx-and-docs.md) | [返回中文索引](../README.md)

## 覆盖模块

- `feishu_bot_sdk.docx` -> `DocxService` / `AsyncDocxService`
- `feishu_bot_sdk.docx_document` -> `DocxDocumentService` / `AsyncDocxDocumentService`
- `feishu_bot_sdk.docx_blocks` -> `DocxBlockService` / `AsyncDocxBlockService`
- `feishu_bot_sdk.docs_content` -> `DocContentService` / `AsyncDocContentService`

## 快速示例

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

doc_id, doc_url = docx.create_document("任务报告")
docx.append_markdown(doc_id, "# 标题\n\n这是正文。")
docx.grant_edit_permission(doc_id, "ou_xxx", "open_id")
print(doc_url or doc_id)
```

## `DocxService`（高层封装）

- `create_document(title)`
- `append_markdown(document_id, markdown_text)`
- `grant_edit_permission(document_id, member_id, member_id_type="open_id")`

适合快速把 Markdown 产物写入文档。

## `DocxDocumentService`（文档信息/块遍历）

- 文档：`create_document`、`get_document`、`get_raw_content`
- 块列表：`list_blocks`、`iter_blocks`

## `DocxBlockService`（块级操作）

- 查询：`get_block`、`list_children`、`iter_children`
- 创建：`create_children`、`create_descendant`
- 更新：`update_block`、`batch_update`
- 删除：`delete_children_range`
- 内容转换：`convert_content`（支持 markdown/html 转块）

## `DocContentService`（docs/v1/content）

- `get_content(doc_token, doc_type="docx", content_type="markdown", lang=None)`
- `get_markdown(doc_token, doc_type="docx", lang=None)`

适合“导出文档内容”场景。

## 实践建议

- 产出文档优先用 `DocxService.append_markdown`。
- 要做精细块编辑（结构化插入、批量改块）时切换到 `DocxBlockService`。
- 要读取 Markdown 文本用于二次处理时用 `DocContentService.get_markdown`。
