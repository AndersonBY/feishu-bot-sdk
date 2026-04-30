from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import feishu_bot_sdk.cli as cli


def test_event_help_lists_subscribe_shortcut(capsys: Any) -> None:
    code = cli.main(["event", "--help"])

    assert code == 0
    output = capsys.readouterr().out
    assert "+subscribe" in output


def test_event_subscribe_dry_run_outputs_lark_shape(capsys: Any) -> None:
    code = cli.main(
        [
            "event",
            "+subscribe",
            "--as",
            "bot",
            "--app-id",
            "cli_app",
            "--app-secret",
            "cli_secret",
            "--event-types",
            "im.message.receive_v1,contact.user.created_v3",
            "--filter",
            "^im\\.",
            "--output-dir",
            "events",
            "--route",
            "^im=dir:./im",
            "--dry-run",
            "--format",
            "json",
        ]
    )

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["shortcut"] == "event.+subscribe"
    assert payload["params"]["event_types"] == "im.message.receive_v1,contact.user.created_v3"
    assert payload["params"]["filter"] == "^im\\."
    assert payload["params"]["output_dir"] == "events"
    assert payload["params"]["route"] == ["^im=dir:./im"]


def test_event_subscribe_stdin_compact_writes_to_output_dir(
    monkeypatch: Any,
    tmp_path: Path,
    capsys: Any,
) -> None:
    monkeypatch.setenv("FEISHU_EVENT_STATE_PATH", str(tmp_path / "event-state.json"))
    output_dir = tmp_path / "events"
    event_payload = {
        "schema": "2.0",
        "header": {
            "event_id": "evt_1",
            "event_type": "im.message.receive_v1",
            "create_time": "1710000000",
        },
        "event": {
            "sender": {"sender_id": {"open_id": "ou_1"}},
            "message": {"message_id": "om_1", "chat_id": "oc_1"},
        },
    }

    code = cli.main(
        [
            "event",
            "+subscribe",
            "--as",
            "bot",
            "--app-id",
            "cli_app",
            "--app-secret",
            "cli_secret",
            "--stdin",
            "--compact",
            "--output-dir",
            str(output_dir),
            "--format",
            "json",
        ]
    )

    # cli.main cannot pass stdin directly; use Click invocation for stdin paths in implementation tests.
    assert code == 2
    capsys.readouterr()

    from click.testing import CliRunner
    from feishu_bot_sdk.cli.app import app

    result = CliRunner().invoke(
        app,
        [
            "event",
            "+subscribe",
            "--as",
            "bot",
            "--app-id",
            "cli_app",
            "--app-secret",
            "cli_secret",
            "--stdin",
            "--compact",
            "--output-dir",
            str(output_dir),
            "--format",
            "json",
        ],
        input=json.dumps(event_payload),
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["event_type"] == "im.message.receive_v1"
    assert payload["message_id"] == "om_1"
    files = list(output_dir.glob("*.json"))
    assert len(files) == 1
    assert json.loads(files[0].read_text(encoding="utf-8"))["event_id"] == "evt_1"
