from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import feishu_bot_sdk.cli as cli


def test_event_list_and_schema_emit_local_registry(capsys: Any) -> None:
    code = cli.main(["event", "list", "--format", "json"])
    assert code == 0
    rows = json.loads(capsys.readouterr().out)
    assert rows
    keys = {item["key"] for item in rows}
    assert "im.message.receive_v1" in keys

    code = cli.main(["event", "schema", "im.message.receive_v1", "--format", "json"])
    assert code == 0
    schema_payload = json.loads(capsys.readouterr().out)
    assert schema_payload["key"] == "im.message.receive_v1"
    assert schema_payload["event_type"] == "im.message.receive_v1"
    assert schema_payload["schema_snapshot"]["source_commit"] == "b37adfd"
    assert schema_payload["schema_snapshot"]["helpers"] == [
        "envelope.go",
        "fromtype.go",
        "overlay.go",
        "pointer.go",
    ]
    assert schema_payload["jq_root_path"] in {".", ".event"}
    assert "resolved_output_schema" in schema_payload


def test_event_consume_reads_stdin_payload(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setattr(
        "sys.stdin",
        _StringInput(
            json.dumps(
                {
                    "schema": "2.0",
                    "header": {
                        "event_id": "evt_1",
                        "event_type": "im.message.receive_v1",
                    },
                    "event": {
                        "message": {
                            "message_id": "om_1",
                            "chat_id": "oc_1",
                        },
                        "sender": {
                            "sender_id": {
                                "open_id": "ou_1",
                            }
                        },
                    },
                }
            )
        ),
    )

    code = cli.main(["event", "consume", "im.message.receive_v1", "--stdin", "--format", "json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["event_type"] == "im.message.receive_v1"
    assert payload["event_id"] == "evt_1"
    assert payload["message_id"] == "om_1"
    assert payload["chat_id"] == "oc_1"
    assert payload["sender_open_id"] == "ou_1"


def test_event_status_and_stop_use_local_state_file(
    monkeypatch: Any,
    tmp_path: Path,
    capsys: Any,
) -> None:
    state_path = tmp_path / "events" / "state.json"
    monkeypatch.setenv("FEISHU_EVENT_STATE_PATH", str(state_path))

    code = cli.main(["event", "status", "--format", "json"])
    assert code == 0
    status_payload = json.loads(capsys.readouterr().out)
    assert status_payload["running"] is False
    assert status_payload["state_path"] == str(state_path)

    state_path.parent.mkdir(parents=True)
    state_path.write_text(
        json.dumps({"running": True, "pid": 12345, "event_key": "im.message.receive_v1"}),
        encoding="utf-8",
    )

    code = cli.main(["event", "stop", "--format", "json"])
    assert code == 0
    stop_payload = json.loads(capsys.readouterr().out)
    assert stop_payload["stopped"] is True
    assert stop_payload["pid"] == 12345
    assert json.loads(state_path.read_text(encoding="utf-8"))["running"] is False


class _StringInput:
    def __init__(self, value: str) -> None:
        self._value = value

    def read(self, *_args: Any, **_kwargs: Any) -> str:
        return self._value
