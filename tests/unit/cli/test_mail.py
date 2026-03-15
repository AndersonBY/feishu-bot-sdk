import io
import json
from pathlib import Path
from typing import Any

from feishu_bot_sdk import cli
from feishu_bot_sdk.mail import (
    MailAddressService,
    MailGroupMemberService,
    MailGroupService,
    MailMailboxService,
    MailMessageService,
    PublicMailboxMemberService,
    PublicMailboxService,
)


def _set_env(monkeypatch: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")


def test_mail_help_lists_key_groups(capsys: Any) -> None:
    code = cli.main(["mail", "--help"])
    assert code == 0
    output = capsys.readouterr().out
    assert "mailbox" in output
    assert "message" in output
    assert "group" in output
    assert "public-mailbox" in output


def test_mail_address_query_status(monkeypatch: Any, capsys: Any) -> None:
    _set_env(monkeypatch)
    captured: dict[str, Any] = {}

    def _fake_query_status(_self: MailAddressService, email_list: list[str]) -> dict[str, Any]:
        captured["email_list"] = email_list
        return {"user_list": [{"email": email_list[0], "status": 4, "type": 1}]}

    monkeypatch.setattr("feishu_bot_sdk.mail.MailAddressService.query_status", _fake_query_status)

    code = cli.main(
        [
            "mail",
            "address",
            "query-status",
            "--email",
            "ops@example.com",
            "--email",
            "alerts@example.com",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert captured["email_list"] == ["ops@example.com", "alerts@example.com"]
    payload = json.loads(capsys.readouterr().out)
    assert payload["user_list"][0]["email"] == "ops@example.com"


def test_mail_message_list_all(monkeypatch: Any, capsys: Any) -> None:
    _set_env(monkeypatch)
    calls: list[str | None] = []

    def _fake_list_messages(
        _self: MailMessageService,
        user_mailbox_id: str,
        *,
        folder_id: str,
        page_size: int | None = None,
        page_token: str | None = None,
        only_unread: bool | None = None,
    ) -> dict[str, Any]:
        assert user_mailbox_id == "me"
        assert folder_id == "INBOX"
        assert only_unread is True
        calls.append(page_token)
        if page_token == "next_1":
            return {"items": ["msg_2"], "has_more": False}
        return {"items": ["msg_1"], "has_more": True, "page_token": "next_1"}

    monkeypatch.setattr("feishu_bot_sdk.mail.MailMessageService.list_messages", _fake_list_messages)

    code = cli.main(
        [
            "mail",
            "message",
            "list",
            "--user-mailbox-id",
            "me",
            "--folder-id",
            "INBOX",
            "--only-unread",
            "--all",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert calls == [None, "next_1"]
    payload = json.loads(capsys.readouterr().out)
    assert payload["all"] is True
    assert payload["items"] == ["msg_1", "msg_2"]


def test_mail_message_send_markdown_reads_file_and_resolves_base_dir(
    monkeypatch: Any,
    tmp_path: Path,
    capsys: Any,
) -> None:
    _set_env(monkeypatch)
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
            "message",
            "send-markdown",
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


def test_mail_message_send_markdown_requires_recipients(monkeypatch: Any, capsys: Any) -> None:
    _set_env(monkeypatch)

    code = cli.main(
        [
            "mail",
            "message",
            "send-markdown",
            "--user-mailbox-id",
            "me",
            "--markdown",
            "# hello",
        ]
    )
    assert code == 2
    stderr = capsys.readouterr().err
    assert "at least one recipient is required across" in stderr


def test_mailbox_alias_create_and_delete_from_recycle_bin(monkeypatch: Any, capsys: Any) -> None:
    _set_env(monkeypatch)
    alias_captured: dict[str, Any] = {}
    delete_captured: dict[str, Any] = {}

    def _fake_create_alias(_self: MailMailboxService, user_mailbox_id: str, email_alias: str) -> dict[str, Any]:
        alias_captured["user_mailbox_id"] = user_mailbox_id
        alias_captured["email_alias"] = email_alias
        return {"email_alias": email_alias}

    def _fake_delete_from_recycle_bin(
        _self: MailMailboxService,
        user_mailbox_id: str,
        *,
        transfer_mailbox: str | None = None,
    ) -> dict[str, Any]:
        delete_captured["user_mailbox_id"] = user_mailbox_id
        delete_captured["transfer_mailbox"] = transfer_mailbox
        return {"deleted": True}

    monkeypatch.setattr("feishu_bot_sdk.mail.MailMailboxService.create_alias", _fake_create_alias)
    monkeypatch.setattr("feishu_bot_sdk.mail.MailMailboxService.delete_from_recycle_bin", _fake_delete_from_recycle_bin)

    code = cli.main(
        [
            "mail",
            "mailbox",
            "alias",
            "create",
            "--user-mailbox-id",
            "me",
            "--email-alias",
            "alias@example.com",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert alias_captured == {"user_mailbox_id": "me", "email_alias": "alias@example.com"}
    payload = json.loads(capsys.readouterr().out)
    assert payload["email_alias"] == "alias@example.com"

    code = cli.main(
        [
            "mail",
            "mailbox",
            "delete-from-recycle-bin",
            "--user-mailbox-id",
            "me@example.com",
            "--transfer-mailbox",
            "archive@example.com",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert delete_captured == {
        "user_mailbox_id": "me@example.com",
        "transfer_mailbox": "archive@example.com",
    }
    payload = json.loads(capsys.readouterr().out)
    assert payload["deleted"] is True


def test_mail_group_create_and_member_batch_delete_from_stdin(monkeypatch: Any, capsys: Any) -> None:
    _set_env(monkeypatch)
    group_captured: dict[str, Any] = {}
    member_captured: dict[str, Any] = {}

    def _fake_create_mailgroup(_self: MailGroupService, mailgroup: dict[str, Any]) -> dict[str, Any]:
        group_captured["mailgroup"] = mailgroup
        return {"mailgroup_id": "group_1"}

    def _fake_batch_delete_members(
        _self: MailGroupMemberService,
        mailgroup_id: str,
        member_id_list: list[str],
        *,
        user_id_type: str | None = None,
        department_id_type: str | None = None,
    ) -> dict[str, Any]:
        member_captured["mailgroup_id"] = mailgroup_id
        member_captured["member_id_list"] = member_id_list
        member_captured["user_id_type"] = user_id_type
        member_captured["department_id_type"] = department_id_type
        return {"ok": True}

    monkeypatch.setattr("feishu_bot_sdk.mail.MailGroupService.create_mailgroup", _fake_create_mailgroup)
    monkeypatch.setattr("feishu_bot_sdk.mail.MailGroupMemberService.batch_delete_members", _fake_batch_delete_members)

    code = cli.main(
        [
            "mail",
            "group",
            "create",
            "--mailgroup-json",
            '{"email":"ops@example.com","name":"Ops"}',
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert group_captured["mailgroup"] == {"email": "ops@example.com", "name": "Ops"}
    payload = json.loads(capsys.readouterr().out)
    assert payload["mailgroup_id"] == "group_1"

    monkeypatch.setattr("sys.stdin", io.StringIO('["user_1","user_2"]'))
    code = cli.main(
        [
            "mail",
            "group",
            "member",
            "batch-delete",
            "--mailgroup-id",
            "ops@example.com",
            "--user-id-type",
            "open_id",
            "--department-id-type",
            "department_id",
            "--member-ids-stdin",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert member_captured == {
        "mailgroup_id": "ops@example.com",
        "member_id_list": ["user_1", "user_2"],
        "user_id_type": "open_id",
        "department_id_type": "department_id",
    }
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True


def test_mail_public_mailbox_commands(monkeypatch: Any, capsys: Any) -> None:
    _set_env(monkeypatch)
    remove_captured: dict[str, Any] = {}
    member_captured: dict[str, Any] = {}

    def _fake_remove_to_recycle_bin(
        _self: PublicMailboxService,
        public_mailbox_id: str,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        remove_captured["public_mailbox_id"] = public_mailbox_id
        remove_captured["options"] = options
        return {"ok": True}

    def _fake_batch_create_members(
        _self: PublicMailboxMemberService,
        public_mailbox_id: str,
        items: list[dict[str, Any]],
        *,
        user_id_type: str | None = None,
    ) -> dict[str, Any]:
        member_captured["public_mailbox_id"] = public_mailbox_id
        member_captured["items"] = items
        member_captured["user_id_type"] = user_id_type
        return {"created": len(items)}

    monkeypatch.setattr("feishu_bot_sdk.mail.PublicMailboxService.remove_to_recycle_bin", _fake_remove_to_recycle_bin)
    monkeypatch.setattr("feishu_bot_sdk.mail.PublicMailboxMemberService.batch_create_members", _fake_batch_create_members)

    code = cli.main(
        [
            "mail",
            "public-mailbox",
            "remove-to-recycle-bin",
            "--public-mailbox-id",
            "support@example.com",
            "--options-json",
            '{"to_mail_address":"archive@example.com"}',
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert remove_captured == {
        "public_mailbox_id": "support@example.com",
        "options": {"to_mail_address": "archive@example.com"},
    }
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True

    monkeypatch.setattr("sys.stdin", io.StringIO('[{"user_id":"ou_1"},{"user_id":"ou_2"}]'))
    code = cli.main(
        [
            "mail",
            "public-mailbox",
            "member",
            "batch-create",
            "--public-mailbox-id",
            "support@example.com",
            "--user-id-type",
            "open_id",
            "--items-stdin",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert member_captured == {
        "public_mailbox_id": "support@example.com",
        "items": [{"user_id": "ou_1"}, {"user_id": "ou_2"}],
        "user_id_type": "open_id",
    }
    payload = json.loads(capsys.readouterr().out)
    assert payload["created"] == 2
