import io
import json
from pathlib import Path
from typing import Any
from feishu_bot_sdk import cli
from feishu_bot_sdk.im.messages import Message, MessageResponse, MessageService
from feishu_bot_sdk.response import Struct


def test_im_send_markdown_reads_file(
    monkeypatch: Any, tmp_path: Path, capsys: Any
) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    captured: dict[str, Any] = {}

    def _fake_send_markdown(
        _self: MessageService,
        *,
        receive_id_type: str,
        receive_id: str,
        markdown: str,
        locale: str = "zh_cn",
        title: str | None = None,
        uuid: str | None = None,
    ) -> dict[str, str]:
        captured["receive_id_type"] = receive_id_type
        captured["receive_id"] = receive_id
        captured["markdown"] = markdown
        captured["locale"] = locale
        captured["title"] = title
        captured["uuid"] = uuid
        return {"message_id": "om_cli_1"}

    monkeypatch.setattr(
        "feishu_bot_sdk.im.messages.MessageService.send_markdown", _fake_send_markdown
    )

    markdown_file = tmp_path / "sample.md"
    markdown_file.write_text("### hello from file", encoding="utf-8")

    code = cli.main(
        [
            "im",
            "send-markdown",
            "--receive-id",
            "ou_1",
            "--markdown-file",
            str(markdown_file),
        ]
    )
    assert code == 0
    assert captured["receive_id_type"] == "open_id"
    assert captured["receive_id"] == "ou_1"
    assert captured["markdown"] == "### hello from file"

    stdout = capsys.readouterr().out
    assert "message_id" in stdout
    assert "om_cli_1" in stdout


def test_im_send_markdown_requires_input(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    code = cli.main(
        [
            "im",
            "send-markdown",
            "--receive-id",
            "ou_1",
        ]
    )
    assert code == 2

    stderr = capsys.readouterr().err
    assert (
        "exactly one of --markdown, --markdown-file or --markdown-stdin is required"
        in stderr
    )


def test_im_send_markdown_from_stdin(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")
    monkeypatch.setattr("sys.stdin", io.StringIO("### stdin markdown"))

    captured: dict[str, Any] = {}

    def _fake_send_markdown(
        _self: MessageService,
        *,
        receive_id_type: str,
        receive_id: str,
        markdown: str,
        locale: str = "zh_cn",
        title: str | None = None,
        uuid: str | None = None,
    ) -> dict[str, str]:
        captured["markdown"] = markdown
        return {"message_id": "om_stdin_1"}

    monkeypatch.setattr(
        "feishu_bot_sdk.im.messages.MessageService.send_markdown", _fake_send_markdown
    )

    code = cli.main(
        [
            "im",
            "send-markdown",
            "--receive-id",
            "ou_1",
            "--markdown-stdin",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert captured["markdown"] == "### stdin markdown"
    payload = json.loads(capsys.readouterr().out)
    assert payload["message_id"] == "om_stdin_1"


def _message_response_with_struct() -> MessageResponse:
    body_struct = Struct({"content": '{"text":"hello"}'})
    sender_struct = Struct({"id": "cli_sender"})
    raw_message = {
        "message_id": "om_struct_1",
        "chat_id": "oc_struct_1",
        "body": body_struct,
        "sender": sender_struct,
    }
    return MessageResponse(
        code=0,
        msg="success",
        message=Message(
            message_id="om_struct_1",
            chat_id="oc_struct_1",
            root_id=None,
            parent_id=None,
            thread_id=None,
            msg_type="text",
            create_time="1",
            update_time="1",
            deleted=False,
            updated=False,
            raw=raw_message,
        ),
        raw={"code": 0, "msg": "success", "data": raw_message},
    )


def test_im_send_text_json_output_handles_struct_in_dataclass(
    monkeypatch: Any, capsys: Any
) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    monkeypatch.setattr(
        "feishu_bot_sdk.im.messages.MessageService.send_text",
        lambda *_args, **_kwargs: _message_response_with_struct(),
    )

    code = cli.main(
        [
            "im",
            "send-text",
            "--receive-id",
            "ou_1",
            "--text",
            "hello",
            "--format",
            "json",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["message"]["message_id"] == "om_struct_1"
    assert payload["message"]["raw"]["body"]["content"] == '{"text":"hello"}'
    assert payload["raw"]["data"]["sender"]["id"] == "cli_sender"


def test_im_send_text_human_output_handles_struct_in_dataclass(
    monkeypatch: Any, capsys: Any
) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    monkeypatch.setattr(
        "feishu_bot_sdk.im.messages.MessageService.send_text",
        lambda *_args, **_kwargs: _message_response_with_struct(),
    )

    code = cli.main(
        [
            "im",
            "send-text",
            "--receive-id",
            "ou_1",
            "--text",
            "hello",
        ]
    )
    assert code == 0
    stdout = capsys.readouterr().out
    assert "om_struct_1" in stdout
    assert "chat_id" in stdout


def test_to_jsonable_handles_dataclass_with_struct() -> None:
    payload = cli._to_jsonable(_message_response_with_struct())
    assert payload["message"]["raw"]["body"]["content"] == '{"text":"hello"}'
    assert payload["raw"]["data"]["sender"]["id"] == "cli_sender"


def test_im_push_follow_up(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    captured: dict[str, Any] = {}

    def _fake_push_follow_up(
        _self: MessageService,
        message_id: str,
        *,
        follow_ups: list[dict[str, Any]],
    ) -> dict[str, Any]:
        captured["message_id"] = message_id
        captured["follow_ups"] = follow_ups
        return {"ok": True}

    monkeypatch.setattr(
        "feishu_bot_sdk.im.messages.MessageService.push_follow_up", _fake_push_follow_up
    )

    code = cli.main(
        [
            "im",
            "push-follow-up",
            "om_1",
            "--follow-ups-json",
            '[{"content":"继续处理"}]',
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert captured["message_id"] == "om_1"
    assert captured["follow_ups"] == [{"content": "继续处理"}]
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True


def test_im_forward_thread(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    captured: dict[str, Any] = {}

    def _fake_forward_thread(
        _self: MessageService,
        thread_id: str,
        *,
        receive_id_type: str,
        receive_id: str,
        uuid: str | None = None,
    ) -> dict[str, Any]:
        captured["thread_id"] = thread_id
        captured["receive_id_type"] = receive_id_type
        captured["receive_id"] = receive_id
        captured["uuid"] = uuid
        return {"message_id": "om_forward_1"}

    monkeypatch.setattr(
        "feishu_bot_sdk.im.messages.MessageService.forward_thread", _fake_forward_thread
    )

    code = cli.main(
        [
            "im",
            "forward-thread",
            "omt_1",
            "--receive-id-type",
            "chat_id",
            "--receive-id",
            "oc_1",
            "--uuid",
            "dedup-1",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert captured["thread_id"] == "omt_1"
    assert captured["receive_id_type"] == "chat_id"
    assert captured["receive_id"] == "oc_1"
    assert captured["uuid"] == "dedup-1"
    payload = json.loads(capsys.readouterr().out)
    assert payload["message_id"] == "om_forward_1"


def test_im_update_url_previews(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    captured: dict[str, Any] = {}

    def _fake_update_url_previews(
        _self: MessageService,
        *,
        preview_tokens: list[str],
        open_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        captured["preview_tokens"] = preview_tokens
        captured["open_ids"] = open_ids
        return {"ok": True}

    monkeypatch.setattr(
        "feishu_bot_sdk.im.messages.MessageService.batch_update_url_previews",
        _fake_update_url_previews,
    )

    code = cli.main(
        [
            "im",
            "update-url-previews",
            "--preview-token",
            "token_1",
            "--preview-token",
            "token_2",
            "--open-id",
            "ou_1",
            "--format",
            "json",
        ]
    )
    assert code == 0
    assert captured["preview_tokens"] == ["token_1", "token_2"]
    assert captured["open_ids"] == ["ou_1"]
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
