import json
from pathlib import Path
from typing import Any

from click.testing import CliRunner

from feishu_bot_sdk.cli.app import app
from feishu_bot_sdk.im.media import MediaService


def test_media_upload_image_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["media", "upload-image", "--help"])
    assert result.exit_code == 0
    assert "--image-type" in result.output
    assert "PATH" in result.output


def test_media_upload_file_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["media", "upload-file", "--help"])
    assert result.exit_code == 0
    assert "--file-type" in result.output
    assert "--file-name" in result.output
    assert "--duration" in result.output


def test_media_download_file_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["media", "download-file", "--help"])
    assert result.exit_code == 0
    assert "--message-id" in result.output
    assert "--resource-type" in result.output
    assert "FILE_KEY" in result.output
    assert "OUTPUT" in result.output


def test_media_download_file_writes_bytes(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    def _fake_download_file(_self: MediaService, file_key: str) -> bytes:
        assert file_key == "file_1"
        return b"hello-bytes"

    monkeypatch.setattr(
        "feishu_bot_sdk.im.media.MediaService.download_file", _fake_download_file
    )

    output = tmp_path / "demo.bin"
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["media", "download-file", "file_1", str(output), "--format", "json"],
    )
    assert result.exit_code == 0
    assert output.read_bytes() == b"hello-bytes"
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["file_key"] == "file_1"
    assert payload["mode"] == "file"
    assert payload["size"] == 11


def test_media_download_file_resource_type_requires_message_id(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "media",
            "download-file",
            "file_1",
            str(tmp_path / "demo.bin"),
            "--resource-type",
            "file",
            "--format",
            "json",
        ],
    )
    # CliRunner propagates the ValueError as exit_code 1
    assert result.exit_code != 0
