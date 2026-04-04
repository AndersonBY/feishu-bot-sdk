import json
from pathlib import Path
from typing import Any

from feishu_bot_sdk import cli
from feishu_bot_sdk.mail import MailDraftService, MailMessageService, MailThreadService


def test_mail_help_lists_key_groups(capsys: Any) -> None:
    code = cli.main(["mail", "--help"])
    assert code == 0
    output = capsys.readouterr().out
    assert "+send-markdown" in output
    assert "+draft-create" in output
    assert "+thread" in output
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


def test_mail_draft_create_reads_raw_file(
    monkeypatch: Any,
    tmp_path: Path,
    capsys: Any,
) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    captured: dict[str, Any] = {}

    def _fake_create_draft(
        _self: MailDraftService,
        user_mailbox_id: str,
        draft: dict[str, Any],
    ) -> dict[str, Any]:
        captured["user_mailbox_id"] = user_mailbox_id
        captured["draft"] = draft
        return {"draft": {"draft_id": "draft_1"}}

    monkeypatch.setattr("feishu_bot_sdk.mail.MailDraftService.create_draft", _fake_create_draft)

    raw_file = tmp_path / "draft.eml"
    raw_file.write_text("Subject: Demo\n\nhello", encoding="utf-8")

    code = cli.main(
        [
            "mail",
            "+draft-create",
            "--user-mailbox-id",
            "me",
            "--raw-file",
            str(raw_file),
            "--format",
            "json",
        ]
    )

    assert code == 0
    assert captured["user_mailbox_id"] == "me"
    assert captured["draft"] == {"raw": "Subject: Demo\n\nhello"}
    payload = json.loads(capsys.readouterr().out)
    assert payload["draft"]["draft_id"] == "draft_1"


def test_mail_draft_edit_uses_raw_text(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    captured: dict[str, Any] = {}

    def _fake_update_draft(
        _self: MailDraftService,
        user_mailbox_id: str,
        draft_id: str,
        draft: dict[str, Any],
    ) -> dict[str, Any]:
        captured["user_mailbox_id"] = user_mailbox_id
        captured["draft_id"] = draft_id
        captured["draft"] = draft
        return {"draft": {"draft_id": draft_id}}

    monkeypatch.setattr("feishu_bot_sdk.mail.MailDraftService.update_draft", _fake_update_draft)

    code = cli.main(
        [
            "mail",
            "+draft-edit",
            "--user-mailbox-id",
            "me",
            "--draft-id",
            "draft_2",
            "--raw",
            "Subject: Updated\n\nbody",
            "--format",
            "json",
        ]
    )

    assert code == 0
    assert captured == {
        "user_mailbox_id": "me",
        "draft_id": "draft_2",
        "draft": {"raw": "Subject: Updated\n\nbody"},
    }
    payload = json.loads(capsys.readouterr().out)
    assert payload["draft"]["draft_id"] == "draft_2"


def test_mail_thread_shortcut(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    captured: dict[str, Any] = {}

    def _fake_get_thread(
        _self: MailThreadService,
        user_mailbox_id: str,
        thread_id: str,
        *,
        format: str | None = None,
        include_spam_trash: bool | None = None,
    ) -> dict[str, Any]:
        captured["user_mailbox_id"] = user_mailbox_id
        captured["thread_id"] = thread_id
        captured["format"] = format
        captured["include_spam_trash"] = include_spam_trash
        return {"thread": {"thread_id": thread_id}}

    monkeypatch.setattr("feishu_bot_sdk.mail.MailThreadService.get_thread", _fake_get_thread)

    code = cli.main(
        [
            "mail",
            "+thread",
            "--user-mailbox-id",
            "me",
            "--thread-id",
            "th_1",
            "--thread-format",
            "metadata",
            "--include-spam-trash",
            "--format",
            "json",
        ]
    )

    assert code == 0
    assert captured == {
        "user_mailbox_id": "me",
        "thread_id": "th_1",
        "format": "metadata",
        "include_spam_trash": True,
    }
    payload = json.loads(capsys.readouterr().out)
    assert payload["thread"]["thread_id"] == "th_1"
