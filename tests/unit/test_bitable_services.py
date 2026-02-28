import asyncio
from types import SimpleNamespace
from typing import Any, Mapping, Optional, cast

from feishu_bot_sdk.bitable import AsyncBitableService, BitableService
from feishu_bot_sdk.feishu import AsyncFeishuClient, FeishuClient


class _SyncClientStub:
    def __init__(self, resolver: Any) -> None:
        self._resolver = resolver
        self.calls: list[dict[str, Any]] = []
        self.config = SimpleNamespace(member_permission="edit")

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
    def __init__(self, resolver: Any) -> None:
        self._resolver = resolver
        self.calls: list[dict[str, Any]] = []
        self.config = SimpleNamespace(member_permission="edit")

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


def test_iter_tables_with_pagination():
    def resolver(call: Mapping[str, Any]) -> Mapping[str, Any]:
        page_token = call["params"].get("page_token")
        if page_token == "p2":
            return {"code": 0, "data": {"items": [{"table_id": "tbl_2"}], "has_more": False}}
        return {
            "code": 0,
            "data": {
                "items": [{"table_id": "tbl_1"}],
                "has_more": True,
                "page_token": "p2",
            },
        }

    stub = _SyncClientStub(resolver)
    service = BitableService(cast(FeishuClient, stub))

    items = list(service.iter_tables("app_1", page_size=1))

    assert items == [{"table_id": "tbl_1"}, {"table_id": "tbl_2"}]
    assert len(stub.calls) == 2
    assert stub.calls[0]["path"] == "/bitable/v1/apps/app_1/tables"
    assert stub.calls[0]["params"] == {"page_size": 1}
    assert stub.calls[1]["params"] == {"page_size": 1, "page_token": "p2"}


def test_record_crud_payloads():
    def resolver(_call: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"code": 0, "data": {"ok": True}}

    stub = _SyncClientStub(resolver)
    service = BitableService(cast(FeishuClient, stub))

    service.create_record(
        "app_1",
        "tbl_1",
        {"任务名称": "测试"},
        user_id_type="open_id",
        client_token="ct_1",
    )
    service.batch_update_records(
        "app_1",
        "tbl_1",
        [{"record_id": "rec_1", "fields": {"任务名称": "更新"}}],
    )
    service.batch_delete_records("app_1", "tbl_1", ["rec_1", "rec_2"])

    assert len(stub.calls) == 3
    create_call = stub.calls[0]
    assert create_call["path"] == "/bitable/v1/apps/app_1/tables/tbl_1/records"
    assert create_call["payload"] == {"fields": {"任务名称": "测试"}}
    assert create_call["params"] == {"user_id_type": "open_id", "client_token": "ct_1"}

    batch_update_call = stub.calls[1]
    assert batch_update_call["path"].endswith("/records/batch_update")
    assert batch_update_call["payload"] == {
        "records": [{"record_id": "rec_1", "fields": {"任务名称": "更新"}}]
    }

    batch_delete_call = stub.calls[2]
    assert batch_delete_call["path"].endswith("/records/batch_delete")
    assert batch_delete_call["payload"] == {"records": ["rec_1", "rec_2"]}


def test_field_create_with_client_token():
    def resolver(_call: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"code": 0, "data": {"field": {"field_id": "fld_1"}}}

    stub = _SyncClientStub(resolver)
    service = BitableService(cast(FeishuClient, stub))

    data = service.create_field(
        "app_1",
        "tbl_1",
        {"field_name": "状态", "type": 3},
        client_token="ct_field",
    )

    assert data == {"field": {"field_id": "fld_1"}}
    call = stub.calls[0]
    assert call["path"] == "/bitable/v1/apps/app_1/tables/tbl_1/fields"
    assert call["params"] == {"client_token": "ct_field"}
    assert call["payload"] == {"field_name": "状态", "type": 3}


def test_async_iter_records():
    def resolver(call: Mapping[str, Any]) -> Mapping[str, Any]:
        page_token = call["params"].get("page_token")
        if page_token == "next":
            return {"code": 0, "data": {"items": [{"record_id": "rec_2"}], "has_more": False}}
        return {
            "code": 0,
            "data": {
                "items": [{"record_id": "rec_1"}],
                "has_more": True,
                "page_token": "next",
            },
        }

    stub = _AsyncClientStub(resolver)
    service = AsyncBitableService(cast(AsyncFeishuClient, stub))

    async def run() -> list[Mapping[str, Any]]:
        output: list[Mapping[str, Any]] = []
        async for item in service.iter_records("app_1", "tbl_1", page_size=1):
            output.append(item)
        return output

    items = asyncio.run(run())
    assert items == [{"record_id": "rec_1"}, {"record_id": "rec_2"}]
    assert len(stub.calls) == 2
    assert stub.calls[0]["path"] == "/bitable/v1/apps/app_1/tables/tbl_1/records"


def test_async_batch_delete_records_payload():
    def resolver(_call: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"code": 0, "data": {}}

    stub = _AsyncClientStub(resolver)
    service = AsyncBitableService(cast(AsyncFeishuClient, stub))

    async def run() -> None:
        await service.batch_delete_records("app_1", "tbl_1", ["rec_a", "rec_b"])

    asyncio.run(run())
    assert len(stub.calls) == 1
    call = stub.calls[0]
    assert call["path"] == "/bitable/v1/apps/app_1/tables/tbl_1/records/batch_delete"
    assert call["payload"] == {"records": ["rec_a", "rec_b"]}
