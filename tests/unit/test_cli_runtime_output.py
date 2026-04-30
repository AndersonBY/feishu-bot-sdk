from __future__ import annotations

import base64
import hashlib
import json
from argparse import Namespace
from typing import Any

from feishu_bot_sdk.cli.runtime import output as output_runtime


def test_print_result_injects_notice_only_for_ok_envelopes(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    monkeypatch.setattr(
        output_runtime,
        "PendingNotice",
        lambda: {"update": {"current": "1.0.0", "latest": "2.0.0"}},
    )

    output_runtime._print_result(
        {"ok": True, "data": "hello"},
        output_format="json",
    )
    envelope = json.loads(capsys.readouterr().out)
    assert envelope["_notice"]["update"]["latest"] == "2.0.0"

    output_runtime._print_result(
        {"name": "not-an-envelope"},
        output_format="json",
    )
    non_envelope = json.loads(capsys.readouterr().out)
    assert "_notice" not in non_envelope


def test_print_error_injects_notice_into_error_envelope(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    monkeypatch.setattr(output_runtime, "PendingNotice", lambda: {"update": "available"})

    code = output_runtime._print_error(
        "bad input",
        exit_code=2,
        output_format="json",
        error_type="validation_error",
    )

    assert code == 2
    envelope = json.loads(capsys.readouterr().out)
    assert envelope["ok"] is False
    assert envelope["_notice"] == {"update": "available"}


def test_binary_result_is_rendered_as_summary(capsys: Any) -> None:
    content = b"\xff\x00abc"

    output_runtime._print_result(content, output_format="json")

    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "_binary": {
            "size_bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
            "preview_base64": base64.b64encode(content).decode("ascii"),
            "preview_truncated": False,
        }
    }


def test_truncation_meta_includes_risk_and_page_all_metadata(capsys: Any) -> None:
    payload = {
        "items": [{"name": "x" * 4000}],
        "has_more": True,
        "page_token": "next_1",
    }

    output_runtime._print_result(
        payload,
        output_format="json",
        max_output_chars=1800,
        cli_args=Namespace(
            page_size=50,
            page_token=None,
            page_all=True,
            risk="high-risk-write",
            yes=True,
        ),
    )

    result = json.loads(capsys.readouterr().out)
    meta = result["_cli_output"]
    assert meta["truncated"] is True
    assert meta["paging"]["all"] is True
    assert meta["paging"]["next_page_token"] == "next_1"
    assert meta["risk"] == {"risk": "high-risk-write", "requires_confirmation": True}

