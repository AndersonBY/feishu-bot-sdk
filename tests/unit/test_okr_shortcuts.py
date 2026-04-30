from __future__ import annotations

from pathlib import Path
from typing import Any

import feishu_bot_sdk.cli as cli
from feishu_bot_sdk.feishu import FeishuClient


OKR_SHORTCUTS = (
    "+cycle-list",
    "+cycle-detail",
    "+progress-list",
    "+progress-get",
    "+progress-create",
    "+progress-update",
    "+progress-delete",
    "+upload-image",
)


def _base() -> list[str]:
    return ["--as", "user", "--user-access-token", "user_token", "--format", "json"]


def test_okr_help_lists_lark_shortcuts(capsys: Any) -> None:
    code = cli.main(["okr", "--help"])

    assert code == 0
    output = capsys.readouterr().out
    for shortcut in OKR_SHORTCUTS:
        assert shortcut in output


def test_okr_cycle_and_progress_read_shortcuts(monkeypatch: Any, capsys: Any) -> None:
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
        return {"code": 0, "data": {"items": [], "has_more": False, "progress_record": {"id": "pr_1"}}}

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)

    assert cli.main(["okr", "+cycle-list", *_base(), "--user-id", "ou_1", "--user-id-type", "open_id"]) == 0
    capsys.readouterr()
    assert cli.main(["okr", "+cycle-detail", *_base(), "--cycle-id", "123"]) == 0
    capsys.readouterr()
    assert cli.main(["okr", "+progress-list", *_base(), "--target-id", "456", "--target-type", "objective"]) == 0
    capsys.readouterr()
    assert cli.main(["okr", "+progress-get", *_base(), "--progress-id", "789"]) == 0

    assert calls[0] == {
        "method": "GET",
        "path": "/okr/v2/cycles",
        "payload": None,
        "params": {"user_id": "ou_1", "user_id_type": "open_id", "page_size": 100},
    }
    assert calls[1]["path"] == "/okr/v2/cycles/123/objectives"
    assert calls[2]["path"] == "/okr/v2/objectives/456/progresses"
    assert calls[2]["params"] == {
        "user_id_type": "open_id",
        "department_id_type": "open_department_id",
        "page_size": 100,
    }
    assert calls[3]["path"] == "/okr/v1/progress_records/789"
    assert calls[3]["params"] == {"user_id_type": "open_id"}


def test_okr_progress_write_shortcuts(monkeypatch: Any, capsys: Any) -> None:
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
        return {"code": 0, "data": {"progress_record": {"id": "pr_1"}}}

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json)

    assert cli.main(
        [
            "okr",
            "+progress-create",
            *_base(),
            "--target-id",
            "456",
            "--target-type",
            "key_result",
            "--content",
            '{"type":"text","text":"Done"}',
            "--progress-percent",
            "80",
            "--progress-status",
            "normal",
        ]
    ) == 0
    capsys.readouterr()
    assert cli.main(
        [
            "okr",
            "+progress-update",
            *_base(),
            "--progress-id",
            "789",
            "--content",
            '{"type":"text","text":"Updated"}',
            "--progress-percent",
            "90",
        ]
    ) == 0
    capsys.readouterr()
    assert cli.main(["okr", "+progress-delete", *_base(), "--progress-id", "789"]) == 0

    assert calls[0] == {
        "method": "POST",
        "path": "/okr/v1/progress_records/",
        "payload": {
            "content": {"type": "text", "text": "Done"},
            "target_id": "456",
            "target_type": 2,
            "progress_rate": {"percent": "80", "status": "normal"},
            "source_title": "created by lark-cli",
        },
        "params": {"user_id_type": "open_id"},
    }
    assert calls[1]["method"] == "PUT"
    assert calls[1]["path"] == "/okr/v1/progress_records/789"
    assert calls[1]["payload"] == {
        "content": {"type": "text", "text": "Updated"},
        "progress_rate": {"percent": "90"},
    }
    assert calls[2] == {
        "method": "DELETE",
        "path": "/okr/v1/progress_records/789",
        "payload": None,
        "params": None,
    }


def test_okr_upload_image_uses_multipart(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    calls: list[dict[str, Any]] = []

    def _fake_request_multipart(
        _self: FeishuClient,
        method: str,
        path: str,
        *,
        data: dict[str, Any] | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        calls.append({"method": method, "path": path, "data": data, "files": files, "params": params})
        return {"code": 0, "data": {"file_token": "img_1"}}

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.request_multipart", _fake_request_multipart)
    image_path = tmp_path / "okr.png"
    image_path.write_bytes(b"image-bytes")

    assert cli.main(
        [
            "okr",
            "+upload-image",
            *_base(),
            "--file",
            str(image_path),
            "--target-id",
            "456",
            "--target-type",
            "objective",
        ]
    ) == 0

    assert calls[0]["method"] == "POST"
    assert calls[0]["path"] == "/okr/v1/images/upload"
    assert calls[0]["data"] == {"target_id": "456", "target_type": "1"}
    assert calls[0]["files"] == {"data": ("okr.png", b"image-bytes", "image/png")}
