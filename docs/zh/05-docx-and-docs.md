# 05 云文档（Docx/Docs Content）

[English](../en/05-docx-and-docs.md) | [返回中文索引](../README.md)

## 覆盖包

- `feishu_bot_sdk.docx` 统一导出：
  `DocxService` / `AsyncDocxService`、
  `DocxDocumentService` / `AsyncDocxDocumentService`、
  `DocxBlockService` / `AsyncDocxBlockService`、
  `DocContentService` / `AsyncDocContentService`
- 包内按职责拆分为 `service` / `document` / `blocks` / `content`
- 日常使用建议直接从 `feishu_bot_sdk.docx` 导入，不需要记内部文件名

## 推荐写法

新版推荐把“写文档”和“读导出内容”拆开看：

- 写文档：优先走 `DocxService.insert_content()`，它会按官方建议执行 `convert -> create_descendant -> replace_image`
- 精细块编辑：使用 `DocxBlockService`
- 读取导出内容：使用 `DocContentService`
- 读取纯文本：使用 `DocxDocumentService.get_raw_content()`

## 快速示例

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

created = docx.create_document("任务报告", folder_token="fld_xxx")
document_id = created["document_id"]

docx.insert_content(
    document_id,
    "# 标题\n\n这是正文。\n\n![logo](https://example.com/logo.png)",
    content_type="markdown",
    document_revision_id=-1,
)
docx.set_title(document_id, "任务报告（已更新）")
docx.grant_edit_permission(document_id, "ou_xxx", "open_id")

print(created["url"] or document_id)
```

## `DocxService`（高层封装）

- 文档：`create_document`
- 内容写入：`insert_content`、`append_markdown`
- 便捷更新：`set_title`、`set_block_text`
- 资源替换：`replace_image`、`replace_file`
- 内容导出：`get_content`
- 授权：`grant_edit_permission`

其中：

- `insert_content` 支持 `markdown` / `html`
- 表格块会在插入前自动去掉只读的 `merge_info`
- Markdown / HTML 转出来的图片会自动下载、上传为 `docx_image` 素材，再调用 `replace_image`

## `DocxDocumentService`（文档信息）

- `create_document(title, folder_token=None)`
- `get_document(document_id)`
- `get_raw_content(document_id, lang=None)`
- `list_blocks(...)`
- `iter_blocks(...)`

## `DocxBlockService`（块级操作）

- 查询：`get_block`、`list_children`、`iter_children`
- 创建：`create_children`、`create_descendant`
- 更新：`update_block`、`batch_update`
- 删除：`delete_children_range`
- 转换：`convert_content(content, content_type="markdown")`

常用官方参数都已补齐：

- 写操作：`document_revision_id`、`client_token`
- 读操作：`user_id_type`
- 子块查询：`with_descendants`

## `DocContentService`（`docs/v1/content`）

- `get_content(doc_token, doc_type="docx", content_type="markdown", lang=None)`
- `get_markdown(doc_token, doc_type="docx", lang=None)`

适合做“导出 Markdown / HTML 再二次处理”。

## 实践建议

- 要把 Markdown/HTML 填进云文档，不要自己拼块，直接用 `DocxService.insert_content`
- 要做局部替换、插入几行、删一段，优先组合 `list_children` / `update_block` / `delete_children_range`
- 要替换图片或附件，先创建空块，再用 `replace_image` / `replace_file`
- 要导出成 Markdown 或 HTML，走 `DocContentService`，不要混用写接口
