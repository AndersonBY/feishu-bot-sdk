from __future__ import annotations

from typing import Any

import feishu_bot_sdk.cli as cli
from feishu_bot_sdk.feishu import FeishuClient


SHEETS_P5_SHORTCUTS = (
    "+info",
    "+read",
    "+write",
    "+write-image",
    "+append",
    "+find",
    "+create",
    "+export",
    "+merge-cells",
    "+unmerge-cells",
    "+replace",
    "+set-style",
    "+batch-set-style",
    "+add-dimension",
    "+insert-dimension",
    "+update-dimension",
    "+move-dimension",
    "+delete-dimension",
    "+create-filter-view",
    "+update-filter-view",
    "+list-filter-views",
    "+get-filter-view",
    "+delete-filter-view",
    "+create-filter-view-condition",
    "+update-filter-view-condition",
    "+list-filter-view-conditions",
    "+get-filter-view-condition",
    "+delete-filter-view-condition",
    "+set-dropdown",
    "+update-dropdown",
    "+get-dropdown",
    "+delete-dropdown",
    "+media-upload",
    "+create-float-image",
    "+update-float-image",
    "+get-float-image",
    "+list-float-images",
    "+delete-float-image",
)


def test_sheets_help_lists_lark_shortcuts(capsys: Any) -> None:
    code = cli.main(["sheets", "--help"])

    assert code == 0
    output = capsys.readouterr().out
    for command in SHEETS_P5_SHORTCUTS:
        assert command in output


def test_sheets_core_shortcuts_build_requests(monkeypatch: Any, tmp_path: Any, capsys: Any) -> None:
    calls: list[dict[str, Any]] = []
    image_path = tmp_path / "chart.png"
    image_path.write_bytes(b"png")

    def _fake_request_json(
        _self: FeishuClient,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        calls.append({"method": method, "path": path, "payload": payload, "params": params})
        if path == "/sheets/v3/spreadsheets":
            return {
                "code": 0,
                "data": {
                    "spreadsheet": {
                        "spreadsheet_token": "sht_1",
                        "url": "https://example.com/sht_1",
                    }
                },
            }
        if path == "/sheets/v3/spreadsheets/sht_1/sheets/query":
            return {"code": 0, "data": {"sheets": [{"sheet_id": "sheet_1", "title": "Sheet1"}]}}
        if path == "/sheets/v2/spreadsheets/sht_1/values_append":
            return {"code": 0, "data": {"updates": {"updatedRows": 2}}}
        if path == "/sheets/v2/spreadsheets/sht_1/values":
            return {"code": 0, "data": {"updatedRange": "sheet_1!A1:B1"}}
        if path == "/sheets/v2/spreadsheets/sht_1/values/sheet_1%21A1%3AB2":
            return {"code": 0, "data": {"valueRange": {"values": [["a"]]}}}
        if path.endswith("/filter_views"):
            return {"code": 0, "data": {"filter_view": {"filter_view_id": "fv_1"}}}
        if path.endswith("/dataValidation"):
            return {"code": 0, "data": {"data_validation_id": "dv_1"}}
        if path.endswith("/float_images"):
            return {"code": 0, "data": {"float_image_id": "img_1"}}
        raise AssertionError(f"unexpected path: {path}")

    def _fake_request_multipart(
        _self: FeishuClient,
        method: str,
        path: str,
        *,
        data: dict[str, object] | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
        params: dict[str, object] | None = None,
    ) -> dict[str, Any]:
        calls.append({"method": method, "path": path, "data": data, "files": files, "params": params})
        return {"code": 0, "data": {"file_token": "media_1"}}

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)
    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_multipart", _fake_request_multipart)
    base = ["--as", "bot", "--access-token", "tenant_token", "--format", "json"]

    assert cli.main(["sheets", "+create", *base, "--title", "Plan", "--headers", '["Name","Score"]', "--data", '[["A",1]]']) == 0
    capsys.readouterr()
    assert cli.main(["sheets", "+read", *base, "--spreadsheet-token", "sht_1", "--sheet-id", "sheet_1", "--range", "A1:B2", "--value-render-option", "ToString"]) == 0
    capsys.readouterr()
    assert cli.main(["sheets", "+write", *base, "--spreadsheet-token", "sht_1", "--sheet-id", "sheet_1", "--range", "A1:B1", "--values", '[["ok",2]]']) == 0
    capsys.readouterr()
    assert cli.main(["sheets", "+media-upload", *base, "--spreadsheet-token", "sht_1", "--file", str(image_path), "--parent-node", "sheet_1"]) == 0
    capsys.readouterr()
    assert cli.main(["sheets", "+create-filter-view", *base, "--spreadsheet-token", "sht_1", "--sheet-id", "sheet_1", "--range", "A1:B5", "--filter-view-name", "Open"]) == 0
    capsys.readouterr()
    assert cli.main(["sheets", "+set-dropdown", *base, "--spreadsheet-token", "sht_1", "--sheet-id", "sheet_1", "--range", "A2:A5", "--options", '["Open","Closed"]']) == 0
    capsys.readouterr()
    assert cli.main(["sheets", "+create-float-image", *base, "--spreadsheet-token", "sht_1", "--sheet-id", "sheet_1", "--file-token", "media_1", "--range", "C3"]) == 0

    assert calls[0]["path"] == "/sheets/v3/spreadsheets"
    assert calls[0]["payload"] == {"title": "Plan"}
    assert calls[1]["path"] == "/sheets/v3/spreadsheets/sht_1/sheets/query"
    assert calls[2]["path"] == "/sheets/v2/spreadsheets/sht_1/values_append"
    assert calls[2]["payload"]["valueRange"]["range"] == "sheet_1"
    assert calls[2]["payload"]["valueRange"]["values"] == [["Name", "Score"], ["A", 1]]
    assert calls[3]["method"] == "GET"
    assert calls[3]["path"] == "/sheets/v2/spreadsheets/sht_1/values/sheet_1%21A1%3AB2"
    assert calls[3]["params"] == {"valueRenderOption": "ToString"}
    assert calls[4]["payload"] == {"valueRange": {"range": "sheet_1!A1:B1", "values": [["ok", 2]]}}
    assert calls[5]["path"] == "/drive/v1/medias/upload_all"
    assert calls[5]["data"]["parent_type"] == "sheet_image"
    assert calls[6]["path"] == "/sheets/v3/spreadsheets/sht_1/sheets/sheet_1/filter_views"
    assert calls[6]["payload"] == {"filter_view_name": "Open", "range": "sheet_1!A1:B5"}
    assert calls[7]["path"] == "/sheets/v2/spreadsheets/sht_1/dataValidation"
    assert calls[7]["payload"]["dataValidation"]["conditionValues"] == ["Open", "Closed"]
    assert calls[8]["path"] == "/sheets/v3/spreadsheets/sht_1/sheets/sheet_1/float_images"


def test_sheets_append_style_dimension_and_query_paths_match_lark_cli(monkeypatch: Any, capsys: Any) -> None:
    calls: list[dict[str, Any]] = []

    def _fake_request_json(
        _self: FeishuClient,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        calls.append({"method": method, "path": path, "payload": payload, "params": params})
        return {"code": 0, "data": {"ok": True}}

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)
    base = ["--as", "bot", "--access-token", "tenant_token", "--format", "json"]

    assert cli.main(["sheets", "+append", *base, "--spreadsheet-token", "sht_1", "--sheet-id", "sheet_1", "--range", "A4", "--values", '[["Carol",3]]']) == 0
    capsys.readouterr()
    assert cli.main(["sheets", "+set-style", *base, "--spreadsheet-token", "sht_1", "--sheet-id", "sheet_1", "--range", "A1", "--style", '{"font":{"bold":true}}']) == 0
    capsys.readouterr()
    assert cli.main(["sheets", "+batch-set-style", *base, "--spreadsheet-token", "sht_1", "--data", '[{"ranges":["sheet_1!A1"],"style":{"font":{"bold":true}}}]']) == 0
    capsys.readouterr()
    assert cli.main(["sheets", "+add-dimension", *base, "--spreadsheet-token", "sht_1", "--sheet-id", "sheet_1", "--dimension", "ROWS", "--length", "1"]) == 0
    capsys.readouterr()
    assert cli.main(["sheets", "+insert-dimension", *base, "--spreadsheet-token", "sht_1", "--sheet-id", "sheet_1", "--dimension", "ROWS", "--start-index", "1", "--end-index", "2"]) == 0
    capsys.readouterr()
    assert cli.main(["sheets", "+update-dimension", *base, "--spreadsheet-token", "sht_1", "--sheet-id", "sheet_1", "--dimension", "ROWS", "--start-index", "1", "--end-index", "1", "--fixed-size", "32"]) == 0
    capsys.readouterr()
    assert cli.main(["sheets", "+move-dimension", *base, "--spreadsheet-token", "sht_1", "--sheet-id", "sheet_1", "--dimension", "ROWS", "--start-index", "0", "--end-index", "0", "--destination-index", "2"]) == 0
    capsys.readouterr()
    assert cli.main(["sheets", "+delete-dimension", *base, "--spreadsheet-token", "sht_1", "--sheet-id", "sheet_1", "--dimension", "ROWS", "--start-index", "2", "--end-index", "2"]) == 0
    capsys.readouterr()
    assert cli.main(["sheets", "+list-filter-views", *base, "--spreadsheet-token", "sht_1", "--sheet-id", "sheet_1"]) == 0
    capsys.readouterr()
    assert cli.main(["sheets", "+set-dropdown", *base, "--spreadsheet-token", "sht_1", "--range", "sheet_1!B2:B5", "--condition-values", '["Open","Closed"]']) == 0
    capsys.readouterr()
    assert cli.main(["sheets", "+get-dropdown", *base, "--spreadsheet-token", "sht_1", "--range", "sheet_1!B2:B5"]) == 0
    capsys.readouterr()
    assert cli.main(["sheets", "+list-float-images", *base, "--spreadsheet-token", "sht_1", "--sheet-id", "sheet_1"]) == 0

    assert calls[0]["path"] == "/sheets/v2/spreadsheets/sht_1/values_append"
    assert calls[0]["payload"]["valueRange"]["range"] == "sheet_1!A4:A4"
    assert calls[1]["path"] == "/sheets/v2/spreadsheets/sht_1/style"
    assert calls[1]["payload"]["appendStyle"]["range"] == "sheet_1!A1:A1"
    assert calls[2]["path"] == "/sheets/v2/spreadsheets/sht_1/styles_batch_update"
    assert calls[2]["payload"]["data"][0]["ranges"] == ["sheet_1!A1:A1"]
    assert calls[3]["method"] == "POST"
    assert calls[3]["path"] == "/sheets/v2/spreadsheets/sht_1/dimension_range"
    assert calls[3]["payload"]["dimension"] == {"sheetId": "sheet_1", "majorDimension": "ROWS", "length": 1}
    assert calls[4]["path"] == "/sheets/v2/spreadsheets/sht_1/insert_dimension_range"
    assert calls[5]["method"] == "PUT"
    assert calls[5]["path"] == "/sheets/v2/spreadsheets/sht_1/dimension_range"
    assert calls[5]["payload"]["dimensionProperties"] == {"fixedSize": 32}
    assert calls[6]["path"] == "/sheets/v3/spreadsheets/sht_1/sheets/sheet_1/move_dimension"
    assert calls[6]["payload"] == {
        "source": {"major_dimension": "ROWS", "start_index": 0, "end_index": 0},
        "destination_index": 2,
    }
    assert calls[7]["method"] == "DELETE"
    assert calls[7]["path"] == "/sheets/v2/spreadsheets/sht_1/dimension_range"
    assert calls[8]["path"] == "/sheets/v3/spreadsheets/sht_1/sheets/sheet_1/filter_views/query"
    assert calls[9]["path"] == "/sheets/v2/spreadsheets/sht_1/dataValidation"
    assert calls[9]["payload"]["dataValidation"]["conditionValues"] == ["Open", "Closed"]
    assert calls[10]["path"] == "/sheets/v2/spreadsheets/sht_1/dataValidation"
    assert calls[10]["params"] == {"range": "sheet_1!B2:B5", "dataValidationType": "list"}
    assert calls[11]["path"] == "/sheets/v3/spreadsheets/sht_1/sheets/sheet_1/float_images/query"
