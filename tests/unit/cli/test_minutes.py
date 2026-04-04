import json
from typing import Any

from feishu_bot_sdk import cli
from feishu_bot_sdk.minutes import MinutesService


def test_minutes_download_url_only(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    monkeypatch.setattr(
        MinutesService,
        "get_minute_media_download_url",
        lambda _self, minute_token: {"download_url": f"https://download.example.com/{minute_token}.mp4"},
    )

    code = cli.main(
        [
            "minutes",
            "+download",
            "--minute-tokens",
            "min_1",
            "--url-only",
            "--format",
            "json",
        ]
    )

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["minute_token"] == "min_1"
    assert payload["download_url"] == "https://download.example.com/min_1.mp4"


def test_minutes_download_saves_file(monkeypatch: Any, tmp_path: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    monkeypatch.setattr(
        MinutesService,
        "get_minute_media_download_url",
        lambda _self, minute_token: {"download_url": f"https://download.example.com/{minute_token}.mp4"},
    )

    class _FakeResponse:
        status_code = 200
        content = b"minute-bytes"
        text = ""
        headers = {
            "content-disposition": 'attachment; filename="meeting.mp4"',
            "content-type": "video/mp4",
        }

        def __init__(self) -> None:
            self.url = type("_URL", (), {"path": "/media/meeting.mp4"})()

        def raise_for_status(self) -> None:
            return None

    class _FakeClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            return None

        def __enter__(self) -> "_FakeClient":
            return self

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
            return False

        def get(self, url: str) -> _FakeResponse:
            assert url == "https://download.example.com/min_1.mp4"
            return _FakeResponse()

    monkeypatch.setattr("feishu_bot_sdk.cli.commands.minutes.httpx.Client", _FakeClient)

    output_path = tmp_path / "downloads"
    output_path.mkdir()
    code = cli.main(
        [
            "minutes",
            "+download",
            "--minute-tokens",
            "min_1",
            "--output",
            str(output_path),
            "--format",
            "json",
        ]
    )

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["size_bytes"] == 12
    saved_path = tmp_path / "downloads" / "meeting.mp4"
    assert payload["saved_path"] == str(saved_path)
    assert saved_path.read_bytes() == b"minute-bytes"
