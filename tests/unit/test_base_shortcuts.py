from __future__ import annotations

from pathlib import Path
from typing import Any

import feishu_bot_sdk.cli as cli
from feishu_bot_sdk.feishu import FeishuClient


BASE_SHORTCUTS = (
    "+advperm-disable",
    "+advperm-enable",
    "+base-copy",
    "+base-create",
    "+base-get",
    "+dashboard-arrange",
    "+dashboard-block-create",
    "+dashboard-block-delete",
    "+dashboard-block-get",
    "+dashboard-block-list",
    "+dashboard-block-update",
    "+dashboard-create",
    "+dashboard-delete",
    "+dashboard-get",
    "+dashboard-list",
    "+dashboard-update",
    "+data-query",
    "+field-create",
    "+field-delete",
    "+field-get",
    "+field-list",
    "+field-search-options",
    "+field-update",
    "+form-create",
    "+form-delete",
    "+form-get",
    "+form-list",
    "+form-questions-create",
    "+form-questions-delete",
    "+form-questions-list",
    "+form-questions-update",
    "+form-update",
    "+record-batch-create",
    "+record-batch-update",
    "+record-delete",
    "+record-get",
    "+record-history-list",
    "+record-list",
    "+record-search",
    "+record-share-link-create",
    "+record-upload-attachment",
    "+record-upsert",
    "+role-create",
    "+role-delete",
    "+role-get",
    "+role-list",
    "+role-update",
    "+table-create",
    "+table-delete",
    "+table-get",
    "+table-list",
    "+table-update",
    "+view-create",
    "+view-delete",
    "+view-get",
    "+view-get-card",
    "+view-get-filter",
    "+view-get-group",
    "+view-get-sort",
    "+view-get-timebar",
    "+view-get-visible-fields",
    "+view-list",
    "+view-rename",
    "+view-set-card",
    "+view-set-filter",
    "+view-set-group",
    "+view-set-sort",
    "+view-set-timebar",
    "+view-set-visible-fields",
    "+workflow-create",
    "+workflow-disable",
    "+workflow-enable",
    "+workflow-get",
    "+workflow-list",
    "+workflow-update",
)


def _base() -> list[str]:
    return ["--as", "user", "--user-access-token", "user_token", "--format", "json"]


def test_base_help_lists_lark_shortcuts(capsys: Any) -> None:
    code = cli.main(["base", "--help"])

    assert code == 0
    output = capsys.readouterr().out
    for shortcut in BASE_SHORTCUTS:
        assert shortcut in output


def test_base_table_field_view_record_requests(monkeypatch: Any, capsys: Any) -> None:
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
        return {"code": 0, "data": {"items": [], "record": {"record_id": "rec_1"}}}

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)

    assert cli.main(["base", "+table-list", *_base(), "--base-token", "app_1", "--offset", "5", "--limit", "20"]) == 0
    capsys.readouterr()
    assert cli.main(["base", "+field-create", *_base(), "--base-token", "app_1", "--table-id", "tbl_1", "--json", '{"field_name":"Name","type":1}']) == 0
    capsys.readouterr()
    assert cli.main(["base", "+view-set-filter", *_base(), "--base-token", "app_1", "--table-id", "tbl_1", "--view-id", "viw_1", "--json", '{"conditions":[]}']) == 0
    capsys.readouterr()
    assert cli.main(["base", "+record-upsert", *_base(), "--base-token", "app_1", "--table-id", "tbl_1", "--json", '{"Name":"Alice"}']) == 0
    capsys.readouterr()
    assert cli.main(["base", "+record-upsert", *_base(), "--base-token", "app_1", "--table-id", "tbl_1", "--record-id", "rec_1", "--json", '{"Name":"Bob"}']) == 0

    assert calls[0] == {
        "method": "GET",
        "path": "/base/v3/bases/app_1/tables",
        "payload": None,
        "params": {"offset": 5, "limit": 20},
    }
    assert calls[1] == {
        "method": "POST",
        "path": "/base/v3/bases/app_1/tables/tbl_1/fields",
        "payload": {"field_name": "Name", "type": 1},
        "params": None,
    }
    assert calls[2] == {
        "method": "PUT",
        "path": "/base/v3/bases/app_1/tables/tbl_1/views/viw_1/filter",
        "payload": {"conditions": []},
        "params": None,
    }
    assert calls[3] == {
        "method": "POST",
        "path": "/base/v3/bases/app_1/tables/tbl_1/records",
        "payload": {"fields": {"Name": "Alice"}},
        "params": None,
    }
    assert calls[4] == {
        "method": "PATCH",
        "path": "/base/v3/bases/app_1/tables/tbl_1/records/rec_1",
        "payload": {"fields": {"Name": "Bob"}},
        "params": None,
    }


def test_base_core_role_advperm_workflow_form_dashboard_requests(monkeypatch: Any, capsys: Any) -> None:
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

    assert cli.main(["base", "+base-create", *_base(), "--name", "Ops", "--folder-token", "fld_1", "--time-zone", "Asia/Shanghai"]) == 0
    capsys.readouterr()
    assert cli.main(["base", "+role-create", *_base(), "--base-token", "app_1", "--json", '{"role_name":"Reviewer"}']) == 0
    capsys.readouterr()
    assert cli.main(["base", "+advperm-enable", *_base(), "--base-token", "app_1"]) == 0
    capsys.readouterr()
    assert cli.main(["base", "+workflow-list", *_base(), "--base-token", "app_1", "--status", "enabled"]) == 0
    capsys.readouterr()
    assert cli.main(["base", "+form-questions-create", *_base(), "--base-token", "app_1", "--table-id", "tbl_1", "--form-id", "frm_1", "--questions", '[{"title":"Name","type":"text"}]']) == 0
    capsys.readouterr()
    assert cli.main(["base", "+dashboard-block-create", *_base(), "--base-token", "app_1", "--dashboard-id", "dash_1", "--name", "Sales", "--type", "bar", "--data-config", '{"table_name":"Orders"}']) == 0

    assert calls[0] == {
        "method": "POST",
        "path": "/base/v3/bases",
        "payload": {"name": "Ops", "folder_token": "fld_1", "time_zone": "Asia/Shanghai"},
        "params": None,
    }
    assert calls[1]["path"] == "/base/v3/bases/app_1/roles"
    assert calls[1]["payload"] == {"role_name": "Reviewer"}
    assert calls[2] == {
        "method": "PUT",
        "path": "/base/v3/bases/app_1/advperm/enable",
        "payload": None,
        "params": {"enable": True},
    }
    assert calls[3] == {
        "method": "POST",
        "path": "/base/v3/bases/app_1/workflows/list",
        "payload": {"status": "enabled", "page_size": 100},
        "params": None,
    }
    assert calls[4]["path"] == "/base/v3/bases/app_1/tables/tbl_1/forms/frm_1/questions"
    assert calls[4]["payload"] == {"questions": [{"title": "Name", "type": "text"}]}
    assert calls[5]["path"] == "/base/v3/bases/app_1/dashboards/dash_1/blocks"
    assert calls[5]["payload"] == {
        "name": "Sales",
        "type": "bar",
        "data_config": {"table_name": "Orders"},
    }


def test_base_record_upload_attachment_uses_multipart_then_patch(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    multipart_calls: list[dict[str, Any]] = []
    json_calls: list[dict[str, Any]] = []

    def _fake_request_multipart(
        _self: FeishuClient,
        method: str,
        path: str,
        *,
        data: dict[str, Any] | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        multipart_calls.append({"method": method, "path": path, "data": data, "files": files, "params": params})
        return {"code": 0, "data": {"file_token": "file_1"}}

    def _fake_request_json(
        _self: FeishuClient,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        json_calls.append({"method": method, "path": path, "payload": payload, "params": params})
        return {"code": 0, "data": {"record": {"record_id": "rec_1"}}}

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_multipart", _fake_request_multipart)
    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)
    attachment_path = tmp_path / "brief.txt"
    attachment_path.write_text("hello", encoding="utf-8")

    assert cli.main(
        [
            "base",
            "+record-upload-attachment",
            *_base(),
            "--base-token",
            "app_1",
            "--table-id",
            "tbl_1",
            "--record-id",
            "rec_1",
            "--field-id",
            "fld_1",
            "--file",
            str(attachment_path),
            "--name",
            "brief.txt",
        ]
    ) == 0

    assert multipart_calls[0]["method"] == "POST"
    assert multipart_calls[0]["path"] == "/drive/v1/medias/upload_all"
    assert multipart_calls[0]["data"]["file_name"] == "brief.txt"
    assert multipart_calls[0]["files"] == {"file": ("brief.txt", b"hello", "text/plain")}
    assert json_calls[0] == {
        "method": "PATCH",
        "path": "/base/v3/bases/app_1/tables/tbl_1/records/rec_1",
        "payload": {"fields": {"fld_1": [{"file_token": "file_1", "name": "brief.txt"}]}},
        "params": None,
    }
