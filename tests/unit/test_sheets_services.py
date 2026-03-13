import asyncio
from typing import Any, Mapping, Optional, cast

from feishu_bot_sdk.sheets import AsyncSheetsService, SheetsService
from feishu_bot_sdk.feishu import AsyncFeishuClient, FeishuClient


class _SyncClientStub:
    def __init__(self, resolver: Any) -> None:
        self._resolver = resolver
        self.calls: list[dict[str, Any]] = []

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


def test_sheets_core_requests():
    def resolver(_call: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"code": 0, "data": {"ok": True}}

    stub = _SyncClientStub(resolver)
    service = SheetsService(cast(FeishuClient, stub))

    # 1. create_spreadsheet
    service.create_spreadsheet(title="Test", folder_token="fld_xxx")

    # 2. get_spreadsheet_info
    service.get_spreadsheet_info("shtcn_xxx")

    # 3. list_sheets
    service.list_sheets("shtcn_xxx")

    # 4. read_values
    service.read_values("shtcn_xxx", "Sheet1!A1:C10", value_render_option="ToString")

    # 5. write_values
    service.write_values(
        "shtcn_xxx",
        value_range={"range": "Sheet1!A1:B2", "values": [["a", "b"]]},
    )

    # 6. append_values
    service.append_values(
        "shtcn_xxx",
        value_range={"range": "Sheet1!A1:B2", "values": [["c"]]},
        insert_data_option="INSERT_ROWS",
    )

    # 7. find_cells
    service.find_cells(
        "shtcn_xxx",
        "sheet_id_1",
        find="keyword",
        find_condition={"match_case": True},
    )

    assert len(stub.calls) == 7

    # --- create_spreadsheet ---
    c = stub.calls[0]
    assert c["method"] == "POST"
    assert c["path"] == "/sheets/v3/spreadsheets"
    assert c["payload"] == {"title": "Test", "folder_token": "fld_xxx"}
    assert c["params"] == {}

    # --- get_spreadsheet_info ---
    c = stub.calls[1]
    assert c["method"] == "GET"
    assert c["path"] == "/sheets/v3/spreadsheets/shtcn_xxx"
    assert c["payload"] == {}
    assert c["params"] == {}

    # --- list_sheets ---
    c = stub.calls[2]
    assert c["method"] == "GET"
    assert c["path"] == "/sheets/v3/spreadsheets/shtcn_xxx/sheets/query"
    assert c["payload"] == {}
    assert c["params"] == {}

    # --- read_values ---
    c = stub.calls[3]
    assert c["method"] == "GET"
    assert c["path"] == "/sheets/v2/spreadsheets/shtcn_xxx/values/Sheet1!A1:C10"
    assert c["payload"] == {}
    assert c["params"] == {"value_render_option": "ToString"}

    # --- write_values ---
    c = stub.calls[4]
    assert c["method"] == "PUT"
    assert c["path"] == "/sheets/v2/spreadsheets/shtcn_xxx/values"
    assert c["payload"] == {
        "valueRange": {"range": "Sheet1!A1:B2", "values": [["a", "b"]]}
    }
    assert c["params"] == {}

    # --- append_values ---
    c = stub.calls[5]
    assert c["method"] == "POST"
    assert c["path"] == "/sheets/v2/spreadsheets/shtcn_xxx/values_append"
    assert c["payload"] == {
        "valueRange": {"range": "Sheet1!A1:B2", "values": [["c"]]},
        "insertDataOption": "INSERT_ROWS",
    }
    assert c["params"] == {}

    # --- find_cells ---
    c = stub.calls[6]
    assert c["method"] == "POST"
    assert c["path"] == "/sheets/v3/spreadsheets/shtcn_xxx/sheets/sheet_id_1/find"
    assert c["payload"] == {
        "find": "keyword",
        "find_condition": {"match_case": True},
    }
    assert c["params"] == {}


def test_async_sheets_requests():
    def resolver(_call: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"code": 0, "data": {"ok": True}}

    stub = _AsyncClientStub(resolver)
    service = AsyncSheetsService(cast(AsyncFeishuClient, stub))

    async def run() -> None:
        await service.create_spreadsheet(title="Test", folder_token="fld_xxx")
        await service.read_values(
            "shtcn_xxx", "Sheet1!A1:C10", value_render_option="ToString"
        )

    asyncio.run(run())

    assert len(stub.calls) == 2

    # --- create_spreadsheet ---
    c = stub.calls[0]
    assert c["method"] == "POST"
    assert c["path"] == "/sheets/v3/spreadsheets"
    assert c["payload"] == {"title": "Test", "folder_token": "fld_xxx"}
    assert c["params"] == {}

    # --- read_values ---
    c = stub.calls[1]
    assert c["method"] == "GET"
    assert c["path"] == "/sheets/v2/spreadsheets/shtcn_xxx/values/Sheet1!A1:C10"
    assert c["payload"] == {}
    assert c["params"] == {"value_render_option": "ToString"}
