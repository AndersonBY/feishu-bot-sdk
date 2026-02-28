import asyncio
from types import SimpleNamespace
from typing import Any, Mapping, Optional, cast

from feishu_bot_sdk.docx_blocks import AsyncDocxBlockService, DocxBlockService
from feishu_bot_sdk.docx_document import AsyncDocxDocumentService, DocxDocumentService
from feishu_bot_sdk.feishu import AsyncFeishuClient, FeishuClient


class _SyncClientStub:
    def __init__(self, resolver: Any, *, doc_folder_token: Optional[str] = None) -> None:
        self._resolver = resolver
        self.calls: list[dict[str, Any]] = []
        self.config = SimpleNamespace(doc_folder_token=doc_folder_token)

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
        self.config = SimpleNamespace(doc_folder_token=doc_folder_token)

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

    create_call = stub.calls[0]
    assert create_call["path"] == "/docx/v1/documents/doc_1/blocks/blk_root/children"
    assert create_call["payload"] == {
        "index": 0,
        "children": [{"block_type": 2, "text": {"elements": []}}],
    }
    assert create_call["params"] == {"document_revision_id": -1, "client_token": "ct1"}

    descendant_call = stub.calls[1]
    assert descendant_call["path"] == "/docx/v1/documents/doc_1/blocks/blk_root/descendant"
    assert descendant_call["payload"] == {
        "index": -1,
        "children_id": ["c1"],
        "descendants": [{"block_id": "c1", "block_type": 2}],
    }

    batch_update_call = stub.calls[2]
    assert batch_update_call["path"] == "/docx/v1/documents/doc_1/blocks/batch_update"
    assert batch_update_call["payload"] == {
        "requests": [{"block_id": "blk_1", "update_text_elements": {"elements": []}}]
    }
    assert batch_update_call["params"] == {"user_id_type": "open_id"}

    delete_call = stub.calls[3]
    assert delete_call["path"] == "/docx/v1/documents/doc_1/blocks/blk_root/children/batch_delete"
    assert delete_call["payload"] == {"start_index": 0, "end_index": 1}
    assert delete_call["params"] == {"document_revision_id": -1}

    convert_call = stub.calls[4]
    assert convert_call["path"] == "/docx/v1/documents/blocks/convert"
    assert convert_call["payload"] == {"content_type": "markdown", "content": "## title"}


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
        async for item in block_service.iter_children("doc_1", "blk_root", page_size=1):
            children.append(item)
        return blocks, children

    blocks, children = asyncio.run(run())

    assert blocks == [{"block_id": "b1"}]
    assert children == [{"block_id": "c1"}, {"block_id": "c2"}]
