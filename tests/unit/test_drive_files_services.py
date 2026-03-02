import asyncio
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Mapping, Optional, cast

from feishu_bot_sdk.drive_files import AsyncDriveFileService, DriveFileService
from feishu_bot_sdk.feishu import AsyncFeishuClient, FeishuClient


@dataclass
class _DummyResponse:
    status_code: int = 200
    json_data: Optional[Mapping[str, Any]] = None
    content: bytes = b""
    text: str = ""

    def json(self) -> Mapping[str, Any]:
        if self.json_data is None:
            raise ValueError("json unavailable")
        return self.json_data


class _SyncClientStub:
    def __init__(self, resolver: Any) -> None:
        self._resolver = resolver
        self.calls: list[dict[str, Any]] = []
        self.config = SimpleNamespace(base_url="https://open.feishu.cn/open-apis", timeout_seconds=30.0)

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

    def get_access_token(self) -> str:
        return "tenant-token"


class _AsyncClientStub:
    def __init__(self, resolver: Any) -> None:
        self._resolver = resolver
        self.calls: list[dict[str, Any]] = []
        self.config = SimpleNamespace(base_url="https://open.feishu.cn/open-apis", timeout_seconds=30.0)

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

    async def get_access_token(self) -> str:
        return "tenant-token"


def test_drive_file_import_export_paths():
    def resolver(_call: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"code": 0, "data": {"ok": True}}

    stub = _SyncClientStub(resolver)
    service = DriveFileService(cast(FeishuClient, stub))

    service.create_import_task({"file_token": "file_1", "type": "docx"})
    service.get_import_task("ticket_1")
    service.create_export_task({"token": "doc_1", "type": "docx"})
    service.get_export_task("ticket_2", token="doc_1")

    assert len(stub.calls) == 4
    assert stub.calls[0]["path"] == "/drive/v1/import_tasks"
    assert stub.calls[0]["payload"] == {"file_token": "file_1", "type": "docx"}
    assert stub.calls[1]["path"] == "/drive/v1/import_tasks/ticket_1"
    assert stub.calls[2]["path"] == "/drive/v1/export_tasks"
    assert stub.calls[3]["path"] == "/drive/v1/export_tasks/ticket_2"
    assert stub.calls[3]["params"] == {"token": "doc_1"}


def test_drive_file_upload_uses_multipart(monkeypatch: Any):
    captured: dict[str, Any] = {}

    def fake_request_raw(
        _self: DriveFileService,
        method: str,
        path: str,
        *,
        form_data: Optional[Mapping[str, object]] = None,
        files: Optional[Mapping[str, Any]] = None,
        params: Optional[Mapping[str, object]] = None,
    ) -> _DummyResponse:
        captured["method"] = method
        captured["path"] = path
        captured["form_data"] = dict(form_data or {})
        captured["files"] = dict(files or {})
        captured["params"] = dict(params or {})
        return _DummyResponse(json_data={"code": 0, "data": {"file_token": "file_1"}})

    monkeypatch.setattr(DriveFileService, "_request_raw", fake_request_raw)
    service = DriveFileService(cast(FeishuClient, _SyncClientStub(lambda _call: {"code": 0, "data": {}})))

    data = service.upload_file_bytes(
        "result.csv",
        b"col1,col2",
        parent_type="explorer",
        parent_node="fld_1",
    )

    assert data == {"file_token": "file_1"}
    assert captured["method"] == "POST"
    assert captured["path"] == "/drive/v1/files/upload_all"
    assert captured["params"] == {}
    assert captured["form_data"]["file_name"] == "result.csv"
    assert captured["form_data"]["parent_type"] == "explorer"
    assert captured["form_data"]["parent_node"] == "fld_1"
    assert captured["form_data"]["size"] == 9
    assert "checksum" not in captured["form_data"]
    file_part = captured["files"]["file"]
    assert file_part[0] == "result.csv"
    assert file_part[1] == b"col1,col2"
    assert isinstance(file_part[2], str)


def test_drive_file_upload_forwards_explicit_checksum(monkeypatch: Any):
    captured: dict[str, Any] = {}

    def fake_request_raw(
        _self: DriveFileService,
        method: str,
        path: str,
        *,
        form_data: Optional[Mapping[str, object]] = None,
        files: Optional[Mapping[str, Any]] = None,
        params: Optional[Mapping[str, object]] = None,
    ) -> _DummyResponse:
        captured["method"] = method
        captured["path"] = path
        captured["form_data"] = dict(form_data or {})
        captured["files"] = dict(files or {})
        captured["params"] = dict(params or {})
        return _DummyResponse(json_data={"code": 0, "data": {"file_token": "file_1"}})

    monkeypatch.setattr(DriveFileService, "_request_raw", fake_request_raw)
    service = DriveFileService(cast(FeishuClient, _SyncClientStub(lambda _call: {"code": 0, "data": {}})))

    service.upload_file_bytes(
        "result.csv",
        b"col1,col2",
        parent_type="explorer",
        parent_node="fld_1",
        checksum="abc123",
    )

    assert captured["method"] == "POST"
    assert captured["path"] == "/drive/v1/files/upload_all"
    assert captured["form_data"]["checksum"] == "abc123"


def test_drive_media_download_and_tmp_urls(monkeypatch: Any):
    captured: dict[str, Any] = {}

    def fake_request_raw(
        _self: DriveFileService,
        method: str,
        path: str,
        *,
        form_data: Optional[Mapping[str, object]] = None,
        files: Optional[Mapping[str, Any]] = None,
        params: Optional[Mapping[str, object]] = None,
    ) -> _DummyResponse:
        captured["method"] = method
        captured["path"] = path
        captured["params"] = dict(params or {})
        captured["form_data"] = dict(form_data or {})
        captured["files"] = dict(files or {})
        return _DummyResponse(content=b"media-bytes")

    def resolver(call: Mapping[str, Any]) -> Mapping[str, Any]:
        if call["path"].endswith("batch_get_tmp_download_url"):
            return {"code": 0, "data": {"tmp_download_urls": [{"file_token": "m1"}]}}
        return {"code": 0, "data": {}}

    monkeypatch.setattr(DriveFileService, "_request_raw", fake_request_raw)
    service = DriveFileService(cast(FeishuClient, _SyncClientStub(resolver)))

    content = service.download_media("med_1", extra='{"bitablePerm":{}}')
    data = service.batch_get_media_tmp_download_urls(["med_1", "med_2"], extra='{"bitablePerm":{}}')

    assert content == b"media-bytes"
    assert captured["method"] == "GET"
    assert captured["path"] == "/drive/v1/medias/med_1/download"
    assert captured["params"] == {"extra": '{"bitablePerm":{}}'}
    assert data == {"tmp_download_urls": [{"file_token": "m1"}]}


def test_async_drive_file_upload_part_and_download_export(monkeypatch: Any):
    captured: dict[str, Any] = {}

    async def fake_request_raw(
        _self: AsyncDriveFileService,
        method: str,
        path: str,
        *,
        form_data: Optional[Mapping[str, object]] = None,
        files: Optional[Mapping[str, Any]] = None,
        params: Optional[Mapping[str, object]] = None,
    ) -> _DummyResponse:
        captured["method"] = method
        captured["path"] = path
        captured["form_data"] = dict(form_data or {})
        captured["files"] = dict(files or {})
        captured["params"] = dict(params or {})
        if path.endswith("/download"):
            return _DummyResponse(content=b"export-bytes")
        return _DummyResponse(json_data={"code": 0, "data": {"ok": True}})

    monkeypatch.setattr(AsyncDriveFileService, "_request_raw", fake_request_raw)
    service = AsyncDriveFileService(cast(AsyncFeishuClient, _AsyncClientStub(lambda _call: {"code": 0, "data": {}})))

    async def run() -> bytes:
        await service.upload_part(upload_id="up_1", seq=1, content=b"abc")
        return await service.download_export_file("file_2")

    binary = asyncio.run(run())

    assert binary == b"export-bytes"
    assert captured["method"] == "GET"
    assert captured["path"] == "/drive/v1/export_tasks/file/file_2/download"
