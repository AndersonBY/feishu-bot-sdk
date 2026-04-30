from __future__ import annotations

import sys
from typing import Any, cast

from tools import live_verify_shortcuts as live


def test_runner_cli_forces_default_profile_and_avoids_refresh_threshold(tmp_path, monkeypatch) -> None:
    calls: list[dict[str, Any]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> Any:
        calls.append({"cmd": cmd, "env": kwargs["env"]})

        class Result:
            returncode = 0
            stdout = "{}"
            stderr = ""

        return Result()

    monkeypatch.setattr(live.subprocess, "run", fake_run)
    env = live.build_env({"APP_ID": "cli_xxx", "APP_SECRET": "secret", "FEISHU_PROFILE": "None"})
    runner = live.Runner(run_id="test", out_dir=tmp_path, env=env, timeout=10)

    code, payload, _, _ = runner.cli(["auth", "whoami"], identity="user", timeout=5)

    assert code == 0
    assert payload == {}
    assert calls
    cmd = calls[0]["cmd"]
    assert cmd == [
        sys.executable,
        "-m",
        "feishu_bot_sdk.cli",
        "auth",
        "whoami",
        "--profile",
        "default",
        "--timeout",
        "5",
        "--format",
        "json",
        "--full-output",
    ]
    sent_env = cast(dict[str, str], calls[0]["env"])
    assert sent_env["FEISHU_PROFILE"] == "default"
    assert sent_env["FEISHU_USER_TOKEN_REFRESH_BEFORE_SECONDS"] == "0"


def test_live_general_cases_use_lark_cli_compatible_options(tmp_path, monkeypatch) -> None:
    cases: list[live.Case] = []

    def fake_run_case(_runner: live.Runner, case: live.Case) -> dict[str, Any]:
        cases.append(case)
        return {}

    monkeypatch.setattr(live.Runner, "run_case", fake_run_case)
    runner = live.Runner(run_id="test", out_dir=tmp_path, env={}, timeout=10)
    runner.ctx.update(
        {
            "doc_id": "doc_x",
            "folder_token": "fld_x",
            "sheet_token": "sht_x",
            "sheet_id": "sh_x",
            "task_id": "task_x",
            "child_task_id": "task_child",
            "tasklist_id": "tasklist_x",
            "event_id": "event_x",
            "chat_id": "chat_x",
            "open_id": "ou_x",
            "file_token": "file_x",
        }
    )

    live.run_general_cases(runner)

    by_key = {case.key: case for case in cases}
    assert "--output-dir" in by_key["drive.+export-download"].args
    assert "--output" not in by_key["drive.+export-download"].args
    assert by_key["mail.+triage"].args == ["--mailbox", "me", "--max", "5"]
    assert "--to-email" in by_key["mail.+send-markdown"].args
    assert "--to" not in by_key["mail.+send-markdown"].args
    assert "--overwrite" in by_key["whiteboard.+update"].args
    assert "--yes" not in by_key["whiteboard.+update"].args
    assert "--overwrite" in by_key["docs.+whiteboard-update"].args
    assert "--yes" not in by_key["docs.+whiteboard-update"].args
    assert by_key["sheets.+append"].args == [
        "--spreadsheet-token",
        "sht_x",
        "--sheet-id",
        "sh_x",
        "--range",
        "A5:B5",
        "--values",
        '[["Dave",4]]',
    ]
    assert by_key["sheets.+set-dropdown"].args == [
        "--spreadsheet-token",
        "sht_x",
        "--range",
        "sh_x!B2:B5",
        "--condition-values",
        '["Open","Closed"]',
    ]


def test_live_base_cases_use_bot_fixture_and_nonempty_ids(tmp_path, monkeypatch) -> None:
    cases: list[live.Case] = []

    def fake_run_case(_runner: live.Runner, case: live.Case) -> dict[str, Any]:
        cases.append(case)
        if case.key == "base.+base-create":
            return {"app": {"app_token": "app_x"}}
        if case.key == "base.+base-copy":
            return {"base_token": "copy_x"}
        if case.key == "base.+table-create":
            return {"id": "tbl_x", "views": [{"id": "vew_x"}]}
        if case.key == "base.+field-create":
            return {"fields": [{"field_id": "fld_x"}]}
        if case.key == "base.+view-create":
            return {"view": {"view_id": "viw_x"}}
        if case.key == "base.+record-upsert":
            return {"record": {"record_id": "rec_x"}}
        return {}

    monkeypatch.setattr(live.Runner, "run_case", fake_run_case)
    runner = live.Runner(run_id="test", out_dir=tmp_path, env={}, timeout=10)

    live.run_base_cases(runner)

    assert cases[0].key == "base.+base-create"
    assert cases[0].identity == "bot"
    for case in cases:
        if case.key.startswith("base.+"):
            assert case.identity == "bot"
            assert "" not in case.args
            assert "invalid_table_id" not in case.args
            assert "invalid_field_id" not in case.args
            assert "invalid_view_id" not in case.args
            assert "invalid_record_id" not in case.args
    assert {"type": "bitable", "token": "app_x", "identity": "bot"} in runner.created
    assert {"type": "bitable", "token": "copy_x", "identity": "bot"} in runner.created


def test_live_general_cases_tracks_wiki_nodes_for_cleanup(tmp_path, monkeypatch) -> None:
    def fake_run_case(_runner: live.Runner, case: live.Case) -> dict[str, Any]:
        if case.key == "wiki.+node-create":
            return {
                "space_id": "sp_x",
                "node_token": "node_created",
                "obj_token": "obj_created",
                "obj_type": "docx",
            }
        if case.key == "wiki.+move":
            return {
                "space_id": "sp_x",
                "node_token": "node_moved",
                "obj_token": "doc_x",
                "obj_type": "docx",
            }
        return {}

    monkeypatch.setattr(live.Runner, "run_case", fake_run_case)
    runner = live.Runner(run_id="test", out_dir=tmp_path, env={}, timeout=10)
    runner.ctx.update(
        {
            "doc_id": "doc_x",
            "folder_token": "fld_x",
            "sheet_token": "sht_x",
            "sheet_id": "sh_x",
            "task_id": "task_x",
            "child_task_id": "task_child",
            "tasklist_id": "tasklist_x",
            "event_id": "event_x",
            "chat_id": "chat_x",
            "open_id": "ou_x",
            "file_token": "file_x",
        }
    )

    live.run_general_cases(runner)

    assert {
        "type": "wiki_node",
        "token": "obj_created",
        "space_id": "sp_x",
        "obj_type": "docx",
        "node_token": "node_created",
        "identity": "user",
    } in runner.created
    assert {
        "type": "wiki_node",
        "token": "doc_x",
        "space_id": "sp_x",
        "obj_type": "docx",
        "node_token": "node_moved",
        "identity": "user",
    } in runner.created


def test_cleanup_deletes_wiki_nodes_by_obj_token_and_skips_drive_delete(tmp_path, monkeypatch) -> None:
    run_cases: list[live.Case] = []
    raw_calls: list[dict[str, Any]] = []

    def fake_run_case(_runner: live.Runner, case: live.Case) -> dict[str, Any]:
        run_cases.append(case)
        return {}

    def fake_raw_api(
        _runner: live.Runner,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        identity: str = "user",
        timeout: int | None = None,
    ) -> tuple[int, dict[str, Any] | None, str, int]:
        raw_calls.append({"method": method, "path": path, "params": params, "data": data, "identity": identity, "timeout": timeout})
        return 0, {"code": 0, "data": {"task_id": "task_x"}}, "{}", 12

    monkeypatch.setattr(live.Runner, "run_case", fake_run_case)
    monkeypatch.setattr(live.Runner, "raw_api", fake_raw_api)
    runner = live.Runner(run_id="test", out_dir=tmp_path, env={}, timeout=10)
    runner.created.extend(
        [
            {"type": "docx", "token": "doc_x"},
            {"type": "wiki_node", "token": "doc_x", "space_id": "sp_x", "obj_type": "docx", "node_token": "node_x", "identity": "user"},
        ]
    )

    live.cleanup(runner)

    assert raw_calls == [
        {
            "method": "DELETE",
            "path": "/wiki/v2/spaces/sp_x/nodes/doc_x",
            "params": None,
            "data": {"obj_type": "docx"},
            "identity": "user",
            "timeout": None,
        }
    ]
    assert [case.args for case in run_cases] == []
    assert runner.results[-1].key == "wiki.node.delete.cleanup"
    assert runner.results[-1].status == "pass"


def test_first_prefixed_id_prefers_matching_prefix_over_nested_view_id() -> None:
    payload = {
        "id": "tbl_x",
        "views": [{"id": "vew_x"}],
    }

    assert live.first_item_id(payload, "table_id", "id") == "vew_x"
    assert live.first_prefixed_id(payload, "tbl", "table_id", "id") == "tbl_x"


def test_runner_classifies_real_success_as_pass_and_timeout_as_cli_failed(tmp_path) -> None:
    runner = live.Runner(run_id="test", out_dir=tmp_path, env={}, timeout=10)

    assert runner._classify(0, {"ok": True}, "blocked") == "pass"
    assert runner._classify(
        124,
        {"ok": False, "error": {"type": "timeout", "code": "timeout", "message": "command timed out"}},
        "blocked",
    ) == "cli_failed"
