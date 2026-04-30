from __future__ import annotations

from typing import Any

import feishu_bot_sdk.cli as cli
from feishu_bot_sdk.feishu import FeishuClient


def test_slides_help_lists_lark_shortcuts(capsys: Any) -> None:
    code = cli.main(["slides", "--help"])

    assert code == 0
    output = capsys.readouterr().out
    assert "+create" in output
    assert "+media-upload" in output
    assert "+replace-slide" in output


def test_slides_shortcuts_build_requests(monkeypatch: Any, tmp_path: Any, capsys: Any) -> None:
    calls: list[dict[str, Any]] = []
    image_path = tmp_path / "image.png"
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
        if path == "/slides_ai/v1/xml_presentations":
            return {"code": 0, "data": {"xml_presentation_id": "pres_1", "revision_id": 3}}
        if path == "/slides_ai/v1/xml_presentations/pres_1/slide":
            return {"code": 0, "data": {"slide_id": "slide_1"}}
        if path == "/slides_ai/v1/xml_presentations/pres_1/slide/replace":
            return {"code": 0, "data": {"revision_id": 4}}
        return {"code": 0, "data": {}}

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

    assert cli.main(["slides", "+create", *base, "--title", "Roadmap", "--slides", '["<slide><shape><content/></shape></slide>"]']) == 0
    capsys.readouterr()
    assert cli.main(["slides", "+media-upload", *base, "--presentation", "pres_1", "--file", str(image_path)]) == 0
    capsys.readouterr()
    assert cli.main(["slides", "+replace-slide", *base, "--presentation", "pres_1", "--slide-id", "slide_1", "--parts", '[{"action":"block_replace","block_id":"shape_1","replacement":"<shape><content/></shape>"}]', "--revision-id", "4"]) == 0

    assert calls[0]["method"] == "POST"
    assert calls[0]["path"] == "/slides_ai/v1/xml_presentations"
    assert "Roadmap" in calls[0]["payload"]["xml_presentation"]["content"]
    assert calls[1]["path"] == "/slides_ai/v1/xml_presentations/pres_1/slide"
    assert calls[2]["path"] == "/drive/v1/medias/upload_all"
    assert calls[2]["data"]["parent_type"] == "slide_file"
    assert calls[2]["data"]["parent_node"] == "pres_1"
    assert calls[3]["path"] == "/slides_ai/v1/xml_presentations/pres_1/slide/replace"
    assert calls[3]["params"] == {"slide_id": "slide_1", "revision_id": 4}
    assert calls[3]["payload"]["parts"][0]["block_id"] == "shape_1"
