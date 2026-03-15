import json
from pathlib import Path
from typing import Any
from feishu_bot_sdk import cli
from feishu_bot_sdk.im.media import MediaService


def test_media_download_file_writes_bytes(
    monkeypatch: Any, tmp_path: Path, capsys: Any
) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    def _fake_download_file(_self: MediaService, file_key: str) -> bytes:
        assert file_key == "file_1"
        return b"hello-bytes"

    monkeypatch.setattr(
        "feishu_bot_sdk.im.media.MediaService.download_file", _fake_download_file
    )

    output = tmp_path / "downloads" / "demo.bin"
    code = cli.main(
        [
            "media",
            "download-file",
            "file_1",
            str(output),
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert output.read_bytes() == b"hello-bytes"
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["file_key"] == "file_1"
    assert payload["mode"] == "file"
    assert payload["size"] == 11


def test_media_download_file_image_key_uses_image_endpoint(
    monkeypatch: Any, tmp_path: Path, capsys: Any
) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    def _fake_download_image(_self: MediaService, image_key: str) -> bytes:
        assert image_key == "img_v3_xxx"
        return b"image-bytes"

    monkeypatch.setattr(
        "feishu_bot_sdk.im.media.MediaService.download_image", _fake_download_image
    )

    output = tmp_path / "downloads" / "image.jpg"
    code = cli.main(
        [
            "media",
            "download-file",
            "img_v3_xxx",
            str(output),
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert output.read_bytes() == b"image-bytes"
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["file_key"] == "img_v3_xxx"
    assert payload["mode"] == "image"


def test_media_download_file_message_resource(
    monkeypatch: Any, tmp_path: Path, capsys: Any
) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    def _fake_download_message_resource(
        _self: MediaService,
        message_id: str,
        file_key: str,
        *,
        resource_type: str,
    ) -> bytes:
        assert message_id == "om_1"
        assert file_key == "img_v3_xxx"
        assert resource_type == "image"
        return b"resource-bytes"

    monkeypatch.setattr(
        "feishu_bot_sdk.im.media.MediaService.download_message_resource",
        _fake_download_message_resource,
    )

    output = tmp_path / "downloads" / "message-resource.jpg"
    code = cli.main(
        [
            "media",
            "download-file",
            "img_v3_xxx",
            str(output),
            "--message-id",
            "om_1",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert output.read_bytes() == b"resource-bytes"
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["mode"] == "message_resource"
    assert payload["message_id"] == "om_1"


def test_media_download_file_resource_type_requires_message_id(
    monkeypatch: Any, capsys: Any
) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    code = cli.main(
        [
            "media",
            "download-file",
            "file_1",
            "demo.bin",
            "--resource-type",
            "file",
            "--format",
            "json",
        ]
    )
    assert code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert "--resource-type requires --message-id" in payload["error"]
