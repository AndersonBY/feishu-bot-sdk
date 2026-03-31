import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Optional, cast

from feishu_bot_sdk.docx import (
    AsyncDocxBlockService,
    AsyncDocxDocumentService,
    AsyncDocxService,
    DocxBlockService,
    DocxDocumentService,
    DocxService,
)
from feishu_bot_sdk.feishu import AsyncFeishuClient, FeishuClient


class _SyncClientStub:
    def __init__(
        self,
        resolver: Any,
        *,
        doc_folder_token: Optional[str] = None,
        doc_url_prefix: Optional[str] = None,
    ) -> None:
        self._resolver = resolver
        self.calls: list[dict[str, Any]] = []
        self.config = SimpleNamespace(
            doc_folder_token=doc_folder_token,
            doc_url_prefix=doc_url_prefix,
            member_permission="edit",
        )

    def request_json(
        self,
        method: str,
        path: str,
        *,
        payload: Optional[Mapping[str, object]] = None,
        params: Optional[Mapping[str, object]] = None,
    ) -> Mapping[str, Any]:
        call = {
            "method": method,
            "path": path,
            "payload": dict(payload or {}),
            "params": dict(params or {}),
        }
        self.calls.append(call)
        return self._resolver(call)


class _AsyncClientStub:
    def __init__(self, resolver: Any, *, doc_folder_token: Optional[str] = None) -> None:
        self._resolver = resolver
        self.calls: list[dict[str, Any]] = []
        self.config = SimpleNamespace(
            doc_folder_token=doc_folder_token,
            doc_url_prefix=None,
            member_permission="edit",
        )

    async def request_json(
        self,
        method: str,
        path: str,
        *,
        payload: Optional[Mapping[str, object]] = None,
        params: Optional[Mapping[str, object]] = None,
    ) -> Mapping[str, Any]:
        call = {
            "method": method,
            "path": path,
            "payload": dict(payload or {}),
            "params": dict(params or {}),
        }
        self.calls.append(call)
        return self._resolver(call)


def test_document_create_uses_config_folder_token():
    def resolver(_call: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"code": 0, "data": {"document": {"document_id": "doc_1"}}}

    stub = _SyncClientStub(resolver, doc_folder_token="fld_default")
    service = DocxDocumentService(cast(FeishuClient, stub))

    data = service.create_document("报告")

    assert data == {"document": {"document_id": "doc_1"}}
    call = stub.calls[0]
    assert call["path"] == "/docx/v1/documents"
    assert call["payload"] == {"title": "报告", "folder_token": "fld_default"}


def test_document_get_raw_content_and_list_children_support_official_params():
    def resolver(_call: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"code": 0, "data": {"items": [], "content": "hello"}}

    stub = _SyncClientStub(resolver)
    doc_service = DocxDocumentService(cast(FeishuClient, stub))
    block_service = DocxBlockService(cast(FeishuClient, stub))

    doc_service.get_raw_content("doc_1", lang="zh_cn")
    block_service.list_children(
        "doc_1",
        "blk_root",
        page_size=10,
        document_revision_id=-1,
        with_descendants=True,
        user_id_type="open_id",
    )

    assert stub.calls[0]["path"] == "/docx/v1/documents/doc_1/raw_content"
    assert stub.calls[0]["params"] == {"lang": "zh_cn"}
    assert stub.calls[1]["path"] == "/docx/v1/documents/doc_1/blocks/blk_root/children"
    assert stub.calls[1]["params"] == {
        "page_size": 10,
        "document_revision_id": -1,
        "with_descendants": True,
        "user_id_type": "open_id",
    }


def test_document_iter_blocks_with_pagination():
    def resolver(call: Mapping[str, Any]) -> Mapping[str, Any]:
        if call["params"].get("page_token") == "next":
            return {"code": 0, "data": {"items": [{"block_id": "b2"}], "has_more": False}}
        return {
            "code": 0,
            "data": {
                "items": [{"block_id": "b1"}],
                "has_more": True,
                "page_token": "next",
            },
        }

    stub = _SyncClientStub(resolver)
    service = DocxDocumentService(cast(FeishuClient, stub))

    items = list(service.iter_blocks("doc_1", page_size=1, document_revision_id=-1))

    assert items == [{"block_id": "b1"}, {"block_id": "b2"}]
    assert stub.calls[0]["path"] == "/docx/v1/documents/doc_1/blocks"
    assert stub.calls[0]["params"] == {"page_size": 1, "document_revision_id": -1}
    assert stub.calls[1]["params"] == {"page_size": 1, "page_token": "next", "document_revision_id": -1}


def test_block_create_update_delete_payloads():
    def resolver(_call: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"code": 0, "data": {"ok": True}}

    stub = _SyncClientStub(resolver)
    service = DocxBlockService(cast(FeishuClient, stub))

    service.create_children(
        "doc_1",
        "blk_root",
        children=[{"block_type": 2, "text": {"elements": []}}],
        index=0,
        document_revision_id=-1,
        client_token="ct1",
    )
    service.create_descendant(
        "doc_1",
        "blk_root",
        children_id=["c1"],
        descendants=[{"block_id": "c1", "block_type": 2}],
    )
    service.batch_update(
        "doc_1",
        requests=[{"block_id": "blk_1", "update_text_elements": {"elements": []}}],
        user_id_type="open_id",
    )
    service.delete_children_range(
        "doc_1",
        "blk_root",
        start_index=0,
        end_index=1,
        document_revision_id=-1,
    )
    service.convert_content("## title", content_type="markdown")

    assert len(stub.calls) == 5
    assert stub.calls[0]["path"] == "/docx/v1/documents/doc_1/blocks/blk_root/children"
    assert stub.calls[0]["payload"] == {
        "index": 0,
        "children": [{"block_type": 2, "text": {"elements": []}}],
    }
    assert stub.calls[0]["params"] == {"document_revision_id": -1, "client_token": "ct1"}
    assert stub.calls[1]["path"] == "/docx/v1/documents/doc_1/blocks/blk_root/descendant"
    assert stub.calls[2]["path"] == "/docx/v1/documents/doc_1/blocks/batch_update"
    assert stub.calls[3]["path"] == "/docx/v1/documents/doc_1/blocks/blk_root/children/batch_delete"
    assert stub.calls[4]["path"] == "/docx/v1/documents/blocks/convert"


def test_docx_service_insert_content_uses_convert_insert_and_replace_image(monkeypatch: Any):
    def resolver(call: Mapping[str, Any]) -> Mapping[str, Any]:
        if call["path"] == "/docx/v1/documents/blocks/convert":
            return {
                "code": 0,
                "data": {
                    "first_level_block_ids": ["tmp_root"],
                    "blocks": [
                        {
                            "block_id": "tmp_root",
                            "block_type": 31,
                            "children": ["tmp_image"],
                            "table": {"property": {"merge_info": [{"row_span": 2}]}}
                        },
                        {
                            "block_id": "tmp_image",
                            "block_type": 27,
                            "children": [],
                            "image": {},
                        },
                    ],
                    "block_id_to_image_urls": [
                        {"block_id": "tmp_image", "image_url": "https://example.com/a.png"}
                    ],
                },
            }
        if call["path"] == "/docx/v1/documents/doc_1/blocks/doc_1/descendant":
            return {
                "code": 0,
                "data": {
                    "block_id_relations": [
                        {"temporary_block_id": "tmp_root", "block_id": "blk_root"},
                        {"temporary_block_id": "tmp_image", "block_id": "blk_image"},
                    ]
                },
            }
        return {"code": 0, "data": {"ok": True}}

    uploaded: dict[str, Any] = {}

    def fake_upload_media_bytes(
        _self: Any,
        filename: str,
        content: bytes,
        *,
        parent_type: str,
        parent_node: str,
        extra: str | None = None,
        checksum: str | None = None,
        content_type: str | None = None,
    ) -> Mapping[str, Any]:
        uploaded["filename"] = filename
        uploaded["content"] = content
        uploaded["parent_type"] = parent_type
        uploaded["parent_node"] = parent_node
        uploaded["extra"] = extra
        uploaded["checksum"] = checksum
        uploaded["content_type"] = content_type
        return {"file_token": "file_img_1"}

    monkeypatch.setattr("feishu_bot_sdk.drive.DriveFileService.upload_media_bytes", fake_upload_media_bytes)
    monkeypatch.setattr(
        "feishu_bot_sdk.docx.service._download_binary",
        lambda url, *, base_dir=None: SimpleNamespace(
            content=b"img-bytes",
            file_name="a.png",
            content_type="image/png",
        ),
    )

    stub = _SyncClientStub(resolver, doc_url_prefix="https://tenant.feishu.cn/docx")
    service = DocxService(cast(FeishuClient, stub))

    data = service.insert_content("doc_1", "# title")

    assert data["batch_count"] == 1
    assert uploaded["filename"] == "a.png"
    assert uploaded["parent_type"] == "docx_image"
    assert uploaded["parent_node"] == "blk_image"
    assert stub.calls[0]["path"] == "/docx/v1/documents/blocks/convert"
    assert stub.calls[1]["path"] == "/docx/v1/documents/doc_1/blocks/doc_1/descendant"
    inserted_descendants = stub.calls[1]["payload"]["descendants"]
    assert inserted_descendants[0]["table"]["property"] == {}
    assert stub.calls[2]["path"] == "/docx/v1/documents/doc_1/blocks/blk_image"
    assert stub.calls[2]["payload"] == {"replace_image": {"token": "file_img_1"}}


def test_docx_service_insert_content_resolves_relative_local_images(tmp_path: Path, monkeypatch: Any):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    image_path = image_dir / "chart.png"
    image_path.write_bytes(b"png-bytes")

    def resolver(call: Mapping[str, Any]) -> Mapping[str, Any]:
        if call["path"] == "/docx/v1/documents/blocks/convert":
            return {
                "code": 0,
                "data": {
                    "first_level_block_ids": ["tmp_root"],
                    "blocks": [
                        {"block_id": "tmp_root", "block_type": 2, "children": ["tmp_image"]},
                        {"block_id": "tmp_image", "block_type": 27, "children": [], "image": {}},
                    ],
                    "block_id_to_image_urls": [
                        {"block_id": "tmp_image", "image_url": "images/chart.png"}
                    ],
                },
            }
        if call["path"] == "/docx/v1/documents/doc_1/blocks/doc_1/descendant":
            return {
                "code": 0,
                "data": {
                    "block_id_relations": [
                        {"temporary_block_id": "tmp_root", "block_id": "blk_root"},
                        {"temporary_block_id": "tmp_image", "block_id": "blk_image"},
                    ]
                },
            }
        return {"code": 0, "data": {"ok": True}}

    uploaded: dict[str, Any] = {}

    def fake_upload_media_bytes(
        _self: Any,
        filename: str,
        content: bytes,
        *,
        parent_type: str,
        parent_node: str,
        extra: str | None = None,
        checksum: str | None = None,
        content_type: str | None = None,
    ) -> Mapping[str, Any]:
        uploaded["filename"] = filename
        uploaded["content"] = content
        uploaded["parent_type"] = parent_type
        uploaded["parent_node"] = parent_node
        uploaded["content_type"] = content_type
        return {"file_token": "file_img_1"}

    monkeypatch.setattr("feishu_bot_sdk.drive.DriveFileService.upload_media_bytes", fake_upload_media_bytes)

    stub = _SyncClientStub(resolver)
    service = DocxService(cast(FeishuClient, stub))

    data = service.insert_content("doc_1", "# title", content_base_dir=tmp_path)

    assert data["batch_count"] == 1
    assert uploaded["filename"] == "chart.png"
    assert uploaded["content"] == b"png-bytes"
    assert uploaded["parent_type"] == "docx_image"
    assert uploaded["parent_node"] == "blk_image"
    assert uploaded["content_type"] == "image/png"


def test_async_docx_service_insert_content_resolves_relative_local_images(
    tmp_path: Path, monkeypatch: Any
):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    image_path = image_dir / "chart.png"
    image_path.write_bytes(b"png-bytes")

    def resolver(call: Mapping[str, Any]) -> Mapping[str, Any]:
        if call["path"] == "/docx/v1/documents/blocks/convert":
            return {
                "code": 0,
                "data": {
                    "first_level_block_ids": ["tmp_root"],
                    "blocks": [
                        {"block_id": "tmp_root", "block_type": 2, "children": ["tmp_image"]},
                        {"block_id": "tmp_image", "block_type": 27, "children": [], "image": {}},
                    ],
                    "block_id_to_image_urls": [
                        {"block_id": "tmp_image", "image_url": "images/chart.png"}
                    ],
                },
            }
        if call["path"] == "/docx/v1/documents/doc_1/blocks/doc_1/descendant":
            return {
                "code": 0,
                "data": {
                    "block_id_relations": [
                        {"temporary_block_id": "tmp_root", "block_id": "blk_root"},
                        {"temporary_block_id": "tmp_image", "block_id": "blk_image"},
                    ]
                },
            }
        return {"code": 0, "data": {"ok": True}}

    uploaded: dict[str, Any] = {}

    async def fake_upload_media_bytes(
        _self: Any,
        filename: str,
        content: bytes,
        *,
        parent_type: str,
        parent_node: str,
        extra: str | None = None,
        checksum: str | None = None,
        content_type: str | None = None,
    ) -> Mapping[str, Any]:
        uploaded["filename"] = filename
        uploaded["content"] = content
        uploaded["parent_type"] = parent_type
        uploaded["parent_node"] = parent_node
        uploaded["content_type"] = content_type
        return {"file_token": "file_img_1"}

    monkeypatch.setattr("feishu_bot_sdk.drive.AsyncDriveFileService.upload_media_bytes", fake_upload_media_bytes)

    stub = _AsyncClientStub(resolver)
    service = AsyncDocxService(cast(AsyncFeishuClient, stub))

    data = asyncio.run(service.insert_content("doc_1", "# title", content_base_dir=tmp_path))

    assert data["batch_count"] == 1
    assert uploaded["filename"] == "chart.png"
    assert uploaded["content"] == b"png-bytes"
    assert uploaded["parent_type"] == "docx_image"
    assert uploaded["parent_node"] == "blk_image"
    assert uploaded["content_type"] == "image/png"


def test_async_document_and_block_iterators():
    def resolver(call: Mapping[str, Any]) -> Mapping[str, Any]:
        if call["path"].endswith("/children"):
            if call["params"].get("page_token") == "p2":
                return {"code": 0, "data": {"items": [{"block_id": "c2"}], "has_more": False}}
            return {
                "code": 0,
                "data": {"items": [{"block_id": "c1"}], "has_more": True, "page_token": "p2"},
            }
        if call["path"].endswith("/blocks"):
            return {"code": 0, "data": {"items": [{"block_id": "b1"}], "has_more": False}}
        return {"code": 0, "data": {}}

    stub = _AsyncClientStub(resolver)
    doc_service = AsyncDocxDocumentService(cast(AsyncFeishuClient, stub))
    block_service = AsyncDocxBlockService(cast(AsyncFeishuClient, stub))

    async def run() -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
        blocks: list[Mapping[str, Any]] = []
        async for item in doc_service.iter_blocks("doc_1"):
            blocks.append(item)
        children: list[Mapping[str, Any]] = []
        async for item in block_service.iter_children("doc_1", "blk_root", page_size=1, with_descendants=True):
            children.append(item)
        return blocks, children

    blocks, children = asyncio.run(run())

    assert blocks == [{"block_id": "b1"}]
    assert children == [{"block_id": "c1"}, {"block_id": "c2"}]
    assert stub.calls[1]["params"]["with_descendants"] is True
