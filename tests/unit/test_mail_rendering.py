from pathlib import Path
from typing import Any

from feishu_bot_sdk.mail import render_markdown_email


def test_render_markdown_email_inlines_local_images_and_styles(tmp_path: Path) -> None:
    image_path = tmp_path / "chart.png"
    image_path.write_bytes(b"fake-image-bytes")

    rendered = render_markdown_email(
        "# Daily Report\n\n![Chart](chart.png)\n\n`inline code`",
        base_dir=tmp_path,
    )

    assert rendered.plain_text.startswith("Daily Report")
    assert "inline code" in rendered.plain_text
    assert 'style="font-size:28px;' in rendered.html
    assert "cid:mail-inline-" in rendered.html
    assert len(rendered.inline_images) == 1
    assert rendered.inline_images[0].filename == "chart.png"
    assert rendered.inline_images[0].content == b"fake-image-bytes"


def test_render_markdown_email_raw_latex_mode() -> None:
    rendered = render_markdown_email(
        "Inline math: $x^2 + y^2$",
        latex_mode="raw",
    )

    assert "Inline math:" in rendered.plain_text
    assert "<code" in rendered.html
    assert "x^2 + y^2" in rendered.html
    assert rendered.inline_images == []


def test_render_markdown_email_inlines_remote_images(monkeypatch: Any) -> None:
    class _FakeResponse:
        headers = {"content-type": "image/png"}
        content = b"remote-image-bytes"

        def raise_for_status(self) -> None:
            return None

    captured: dict[str, Any] = {}

    def _fake_get(url: str, **kwargs: Any) -> _FakeResponse:
        captured["url"] = url
        captured["kwargs"] = kwargs
        return _FakeResponse()

    monkeypatch.setattr("feishu_bot_sdk.mail.rendering.httpx.get", _fake_get)

    rendered = render_markdown_email(
        "# Remote\n\n![Chart](https://cdn.example.com/assets/chart.png?sig=1)",
    )

    assert captured["url"] == "https://cdn.example.com/assets/chart.png?sig=1"
    assert "cid:mail-inline-" in rendered.html
    assert len(rendered.inline_images) == 1
    assert rendered.inline_images[0].filename == "chart.png"
    assert rendered.inline_images[0].content == b"remote-image-bytes"
    assert rendered.inline_images[0].path is None
