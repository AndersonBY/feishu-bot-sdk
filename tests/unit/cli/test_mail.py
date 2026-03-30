import json
from pathlib import Path
from typing import Any

from feishu_bot_sdk import cli
from feishu_bot_sdk.mail import MailMessageService


def test_mail_help_lists_key_groups(capsys: Any) -> None:
    code = cli.main(["mail", "--help"])
    assert code == 0
    output = capsys.readouterr().out
    assert "+send-markdown" in output
    assert "user_mailbox" in output


def test_mail_message_send_markdown_reads_file_and_resolves_base_dir(
    monkeypatch: Any,
    tmp_path: Path,
    capsys: Any,
) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")
    captured: dict[str, Any] = {}

    def _fake_send_markdown(
        _self: MailMessageService,
        user_mailbox_id: str,
        *,
        markdown: str,
        to: list[dict[str, Any]] | None = None,
        cc: list[dict[str, Any]] | None = None,
        bcc: list[dict[str, Any]] | None = None,
        subject: str | None = None,
        attachments: list[dict[str, Any]] | None = None,
        dedupe_key: str | None = None,
        head_from: dict[str, Any] | None = None,
        base_dir: str | Path | None = None,
        latex_mode: str = "auto",
    ) -> dict[str, Any]:
        captured["user_mailbox_id"] = user_mailbox_id
        captured["markdown"] = markdown
        captured["to"] = to
        captured["cc"] = cc
        captured["bcc"] = bcc
        captured["subject"] = subject
        captured["attachments"] = attachments
        captured["dedupe_key"] = dedupe_key
        captured["head_from"] = head_from
        captured["base_dir"] = base_dir
        captured["latex_mode"] = latex_mode
        return {"message_id": "mail_cli_1"}

    monkeypatch.setattr("feishu_bot_sdk.mail.MailMessageService.send_markdown", _fake_send_markdown)

    markdown_file = tmp_path / "report.md"
    markdown_file.write_text("# Report\n\n![Chart](chart.png)", encoding="utf-8")

    code = cli.main(
        [
            "mail",
            "+send-markdown",
            "--user-mailbox-id",
            "me",
            "--to-email",
            "user@example.com",
            "--cc-json",
            '[{"mail_address":"cc@example.com","name":"CC"}]',
            "--subject",
            "Daily",
            "--markdown-file",
            str(markdown_file),
            "--dedupe-key",
            "dedupe-1",
            "--head-from-name",
            "Bot",
            "--latex-mode",
            "raw",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert captured["user_mailbox_id"] == "me"
    assert captured["markdown"] == "# Report\n\n![Chart](chart.png)"
    assert captured["to"] == [{"mail_address": "user@example.com"}]
    assert captured["cc"] == [{"mail_address": "cc@example.com", "name": "CC"}]
    assert captured["bcc"] == []
    assert captured["subject"] == "Daily"
    assert captured["attachments"] is None
    assert captured["dedupe_key"] == "dedupe-1"
    assert captured["head_from"] == {"name": "Bot"}
    assert captured["base_dir"] == markdown_file.resolve().parent
    assert captured["latex_mode"] == "raw"
    payload = json.loads(capsys.readouterr().out)
    assert payload["message_id"] == "mail_cli_1"
