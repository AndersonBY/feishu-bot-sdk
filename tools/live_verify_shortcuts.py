#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]


SECRET_PATTERNS = (
    re.compile(r"(Bearer\s+)[A-Za-z0-9._-]+", re.IGNORECASE),
    re.compile(r'("(?:access_token|refresh_token|app_secret|client_secret)"\s*:\s*")[^"]+(")', re.IGNORECASE),
)


@dataclass
class Case:
    service: str
    name: str
    args: list[str]
    identity: str = "user"
    expect: str = "pass"
    note: str = ""
    timeout: int = 45
    cleanup: bool = False

    @property
    def key(self) -> str:
        return f"{self.service}.+{self.name}"


@dataclass
class Result:
    key: str
    status: str
    exit_code: int | None
    identity: str
    args: list[str]
    duration_ms: int
    note: str = ""
    error_code: Any = None
    error_type: str | None = None
    message: str = ""
    output_keys: list[str] = field(default_factory=list)


class Runner:
    def __init__(self, *, run_id: str, out_dir: Path, env: Mapping[str, str], timeout: int) -> None:
        self.run_id = run_id
        self.out_dir = out_dir
        self.env = dict(env)
        self.default_timeout = timeout
        self.ctx: dict[str, Any] = {}
        self.results: list[Result] = []
        self.created: list[dict[str, str]] = []
        self.fixture_dir = out_dir / "fixtures"
        self.fixture_dir.mkdir(parents=True, exist_ok=True)
        (self.fixture_dir / "probe.txt").write_text(f"feishu live verification {run_id}\n", encoding="utf-8")
        (self.fixture_dir / "probe.csv").write_text("name,score\nAlice,1\nBob,2\n", encoding="utf-8")
        self._write_png(self.fixture_dir / "probe.png")

    def _write_png(self, path: Path) -> None:
        # 1x1 transparent PNG.
        path.write_bytes(
            bytes.fromhex(
                "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
                "1f15c4890000000a49444154789c6360000002000100ffff03000006000557bf"
                "ab0000000049454e44ae426082"
            )
        )

    def cli(self, args: list[str], *, identity: str = "user", timeout: int | None = None) -> tuple[int, dict[str, Any] | None, str, int]:
        effective_timeout = timeout or self.default_timeout
        cmd = [
            sys.executable,
            "-m",
            "feishu_bot_sdk.cli",
            *args,
            "--profile",
            "default",
            "--timeout",
            str(effective_timeout),
            "--format",
            "json",
            "--full-output",
        ]
        if _accepts_identity(args):
            cmd.extend(["--as", identity])
        started = time.monotonic()
        try:
            process_timeout = effective_timeout + max(10, int(effective_timeout * 0.25))
            proc = subprocess.run(
                cmd,
                cwd=ROOT,
                env=self.env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=process_timeout,
                check=False,
            )
            elapsed = int((time.monotonic() - started) * 1000)
            raw = self._redact((proc.stdout or "") + (("\nSTDERR:\n" + proc.stderr) if proc.stderr else ""))
            payload = self._parse_payload(proc.stdout)
            return proc.returncode, payload, raw, elapsed
        except subprocess.TimeoutExpired as exc:
            elapsed = int((time.monotonic() - started) * 1000)
            stdout = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            raw = self._redact(stdout + stderr)
            return 124, {"ok": False, "error": {"type": "timeout", "code": "timeout", "message": "command timed out"}}, raw, elapsed

    def raw_api(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        identity: str = "user",
        timeout: int | None = None,
    ) -> tuple[int, dict[str, Any] | None, str, int]:
        args = ["api", method, path]
        if params:
            args += ["--params", json.dumps(params, ensure_ascii=False)]
        if data:
            args += ["--data", json.dumps(data, ensure_ascii=False)]
        return self.cli(args, identity=identity, timeout=timeout)

    def run_case(self, case: Case) -> dict[str, Any] | None:
        code, payload, raw, elapsed = self.cli(
            [case.service, f"+{case.name}", *case.args],
            identity=case.identity,
            timeout=case.timeout,
        )
        status = self._classify(code, payload, case.expect)
        err = payload.get("error") if isinstance(payload, dict) else None
        error = err if isinstance(err, Mapping) else {}
        output_keys = sorted(payload.keys())[:20] if isinstance(payload, dict) and not error else []
        result = Result(
            key=case.key,
            status=status,
            exit_code=code,
            identity=case.identity,
            args=[case.service, f"+{case.name}", *case.args],
            duration_ms=elapsed,
            note=case.note,
            error_code=error.get("code"),
            error_type=str(error.get("type")) if error else None,
            message=self._short_message(error.get("message") if error else raw),
            output_keys=output_keys,
        )
        self.results.append(result)
        self._write_artifact(case.key, payload, raw)
        print(f"{status:12} {case.key:38} exit={code} {result.error_code or ''} {result.message[:100]}", flush=True)
        return payload

    def record_manual(
        self,
        *,
        key: str,
        status: str,
        note: str,
        identity: str = "user",
        error_code: Any = None,
        message: str = "",
    ) -> None:
        self.results.append(
            Result(
                key=key,
                status=status,
                exit_code=None,
                identity=identity,
                args=[],
                duration_ms=0,
                note=note,
                error_code=error_code,
                message=self._short_message(message),
            )
        )
        print(f"{status:12} {key:38} {error_code or ''} {message[:100]}", flush=True)

    def save(self) -> None:
        summary: dict[str, int] = {}
        for result in self.results:
            summary[result.status] = summary.get(result.status, 0) + 1
        payload = {
            "run_id": self.run_id,
            "summary": dict(sorted(summary.items())),
            "total": len(self.results),
            "results": [result.__dict__ for result in self.results],
            "created": self.created,
        }
        (self.out_dir / "live_verification_results.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        lines = [
            f"# Feishu Shortcut Live Verification {self.run_id}",
            "",
            f"Total: {len(self.results)}",
            "",
            "| status | count |",
            "| --- | ---: |",
        ]
        for key, value in sorted(summary.items()):
            lines.append(f"| {key} | {value} |")
        lines.extend(["", "| shortcut | status | identity | code | note |", "| --- | --- | --- | --- | --- |"])
        for result in self.results:
            note = (result.note or result.message or "").replace("|", "\\|")
            lines.append(f"| `{result.key}` | {result.status} | {result.identity} | {result.error_code or ''} | {note} |")
        (self.out_dir / "live_verification_results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _classify(self, code: int, payload: dict[str, Any] | None, expect: str) -> str:
        if code == 0:
            return "pass"
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, Mapping):
                err_type = str(error.get("type") or "")
                err_code = str(error.get("code") or "")
                if err_type == "timeout" or err_code == "timeout":
                    return "cli_failed"
        if expect == "blocked":
            return "api_blocked"
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, Mapping):
                err_type = str(error.get("type") or "")
                err_code = str(error.get("code") or "")
                message = str(error.get("message") or "")
                if err_type in {"feishu_error", "http_error"}:
                    if err_code in {"90215", "1244017"}:
                        return "cli_failed"
                    return "api_blocked"
                if "feishu api failed" in message:
                    return "api_blocked"
        return "cli_failed"

    def _write_artifact(self, key: str, payload: dict[str, Any] | None, raw: str) -> None:
        safe = key.replace(".", "_").replace("+", "")
        artifact = {"payload": payload, "raw": raw[:4000]}
        (self.out_dir / f"{safe}.json").write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")

    def _parse_payload(self, stdout: str) -> dict[str, Any] | None:
        text = stdout.strip()
        if not text:
            return None
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else {"value": parsed}

    def _redact(self, value: str | bytes) -> str:
        text = value.decode(errors="replace") if isinstance(value, bytes) else value
        for pattern in SECRET_PATTERNS:
            text = pattern.sub(r"\1<redacted>\2" if pattern.groups >= 2 else r"\1<redacted>", text)
        return text

    def _short_message(self, value: Any) -> str:
        text = self._redact(str(value or "")).replace("\n", " ")
        return text[:500]


def nested_get(source: Any, *path: str) -> Any:
    current = source
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def first_item_id(payload: Mapping[str, Any], *names: str) -> str:
    for container in ("items", "records", "fields", "views", "forms", "dashboards", "blocks", "tables"):
        items = payload.get(container)
        if isinstance(items, list) and items:
            item = items[0]
            if isinstance(item, Mapping):
                for name in names:
                    value = item.get(name)
                    if value:
                        return str(value)
    for name in names:
        value = payload.get(name)
        if value:
            return str(value)
    for container in ("record", "field", "view", "table", "form", "dashboard", "block"):
        item = payload.get(container)
        if isinstance(item, Mapping):
            for name in names:
                value = item.get(name)
                if value:
                    return str(value)
    return ""


def first_prefixed_id(payload: Mapping[str, Any], prefix: str, *names: str) -> str:
    value = first_item_id(payload, *names)
    if value.startswith(prefix):
        return value
    for name in names:
        direct = payload.get(name)
        if isinstance(direct, str) and direct.startswith(prefix):
            return direct
    for container in ("items", "records", "fields", "views", "forms", "dashboards", "blocks", "tables"):
        items = payload.get(container)
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, Mapping):
                continue
            for name in names:
                nested = item.get(name)
                if isinstance(nested, str) and nested.startswith(prefix):
                    return nested
    return value


def wiki_created_item(payload: Mapping[str, Any], *, identity: str = "user") -> dict[str, str] | None:
    obj_token = str(payload.get("obj_token") or "").strip()
    space_id = str(payload.get("space_id") or payload.get("target_space_id") or "").strip()
    obj_type = str(payload.get("obj_type") or "").strip()
    node_token = str(payload.get("node_token") or payload.get("wiki_token") or "").strip()
    if not obj_token or not space_id or not obj_type:
        return None
    return {
        "type": "wiki_node",
        "token": obj_token,
        "space_id": space_id,
        "obj_type": obj_type,
        "node_token": node_token,
        "identity": identity,
    }


def _accepts_identity(args: list[str]) -> bool:
    return bool(args) and args[0] not in {"auth", "config", "profile", "schema", "doctor", "update", "completion"}


def build_env(source: Mapping[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ if source is None else source)
    env.pop("FEISHU_ACCESS_TOKEN", None)
    env.pop("FEISHU_USER_ACCESS_TOKEN", None)
    env.pop("FEISHU_USER_REFRESH_TOKEN", None)
    env["FEISHU_PROFILE"] = "default"
    env["FEISHU_USER_TOKEN_REFRESH_BEFORE_SECONDS"] = "0"
    app_id = env.get("FEISHU_APP_ID") or env.get("APP_ID")
    app_secret = env.get("FEISHU_APP_SECRET") or env.get("APP_SECRET")
    if app_id:
        env["FEISHU_APP_ID"] = app_id
    if app_secret:
        env["FEISHU_APP_SECRET"] = app_secret
    return env


def create_core_fixtures(r: Runner) -> None:
    who = r.run_case(Case("contact", "get-user", [], identity="user", note="current user"))
    open_id = str(nested_get(who, "user", "open_id") or who.get("open_id") if isinstance(who, Mapping) else "")
    if open_id:
        r.ctx["open_id"] = open_id

    folder = r.run_case(Case("drive", "create-folder", ["--name", f"vv-live-{r.run_id}"], identity="user"))
    folder_token = str(folder.get("folder_token") or "") if isinstance(folder, Mapping) else ""
    if folder_token:
        r.ctx["folder_token"] = folder_token
        r.created.append({"type": "folder", "token": folder_token})

    doc = r.run_case(
        Case(
            "docs",
            "create",
            ["--content", f"<doc><block type=\"text\">vv live {r.run_id}</block></doc>"],
            identity="user",
        )
    )
    doc_id = str(nested_get(doc, "document", "document_id") or "")
    if doc_id:
        r.ctx["doc_id"] = doc_id
        r.created.append({"type": "docx", "token": doc_id})

    sheet = r.run_case(
        Case(
            "sheets",
            "create",
            ["--title", f"vv-live-{r.run_id}", "--headers", '["Name","Score"]', "--data", '[["Alice",1],["Bob",2]]'],
            identity="user",
        )
    )
    if isinstance(sheet, Mapping):
        token = str(sheet.get("spreadsheet_token") or "")
        sheet_id = str(sheet.get("sheet_id") or "")
        if token:
            r.ctx["sheet_token"] = token
            r.created.append({"type": "sheet", "token": token})
        if sheet_id:
            r.ctx["sheet_id"] = sheet_id

    task = r.run_case(Case("task", "create", ["--summary", f"vv-live-{r.run_id}"], identity="user"))
    task_id = str(task.get("guid") or "") if isinstance(task, Mapping) else ""
    if task_id:
        r.ctx["task_id"] = task_id
        r.created.append({"type": "task", "token": task_id})

    child = r.run_case(Case("task", "create", ["--summary", f"vv-live-child-{r.run_id}"], identity="user"))
    child_task_id = str(child.get("guid") or "") if isinstance(child, Mapping) else ""
    if child_task_id:
        r.ctx["child_task_id"] = child_task_id
        r.created.append({"type": "task", "token": child_task_id})

    tasklist = r.run_case(Case("task", "tasklist-create", ["--name", f"vv-live-{r.run_id}"], identity="user"))
    tasklist_id = str(tasklist.get("guid") or "") if isinstance(tasklist, Mapping) else ""
    if tasklist_id:
        r.ctx["tasklist_id"] = tasklist_id

    cal = r.run_case(
        Case(
            "calendar",
            "create",
            [
                "--summary",
                f"vv-live-{r.run_id}",
                "--start",
                "2026-05-01T10:00:00+08:00",
                "--end",
                "2026-05-01T10:15:00+08:00",
            ],
            identity="user",
        )
    )
    event_id = str(cal.get("event_id") or "") if isinstance(cal, Mapping) else ""
    if event_id:
        r.ctx["event_id"] = event_id

    chat = r.run_case(Case("im", "chat-create", ["--type", "group", "--name", f"vv-live-{r.run_id}"], identity="bot"))
    chat_id = str(chat.get("chat_id") or "") if isinstance(chat, Mapping) else ""
    if chat_id:
        r.ctx["chat_id"] = chat_id

    upload = r.run_case(Case("drive", "upload", ["--file", str(r.fixture_dir / "probe.txt"), "--name", f"probe-{r.run_id}.txt"], identity="user"))
    file_token = str(upload.get("file_token") or "") if isinstance(upload, Mapping) else ""
    if file_token:
        r.ctx["file_token"] = file_token
        r.created.append({"type": "file", "token": file_token})


def run_general_cases(r: Runner) -> None:
    c = r.ctx
    file_path = str(r.fixture_dir / "probe.txt")
    png_path = str(r.fixture_dir / "probe.png")
    out_file = str(r.out_dir / "downloaded_probe.txt")
    doc = c.get("doc_id", "missing_doc")
    folder = c.get("folder_token", "")
    sheet = c.get("sheet_token", "missing_sheet")
    sid = c.get("sheet_id", "Sheet1")
    task = c.get("task_id", "missing_task")
    child = c.get("child_task_id", "missing_child")
    tasklist = c.get("tasklist_id", "missing_tasklist")
    event = c.get("event_id", "missing_event")
    chat = c.get("chat_id", "missing_chat")
    user = c.get("open_id", "")
    file_token = c.get("file_token", "missing_file")

    cases = [
        Case("contact", "search-user", ["--query", "毕"], identity="user"),
        Case("docs", "search", ["--query", "vv-live", "--page-size", "5"], identity="user"),
        Case("docs", "fetch", ["--doc", doc], identity="user"),
        Case("docs", "update", ["--doc", doc, "--command", "append", "--content", '<doc><block type="text">append</block></doc>'], identity="user"),
        Case("docs", "media-upload", ["--file", png_path, "--parent-type", "docx_image", "--parent-node", doc, "--doc-id", doc], identity="user"),
        Case("docs", "media-insert", ["--file", png_path, "--doc", doc, "--type", "image"], identity="user"),
        Case("docs", "media-download", ["--token", "invalid_media_token", "--output", str(r.out_dir / "media.bin"), "--overwrite"], identity="user", expect="blocked", note="requires valid media token"),
        Case("docs", "media-preview", ["--token", "invalid_media_token", "--output", str(r.out_dir / "preview.bin"), "--overwrite"], identity="user", expect="blocked", note="requires valid media token"),
        Case("drive", "download", ["--file-token", file_token, "--output", out_file, "--overwrite"], identity="user"),
        Case("drive", "create-shortcut", ["--file-token", file_token, "--type", "file", "--folder-token", folder], identity="user"),
        Case("drive", "add-comment", ["--doc", doc, "--type", "docx", "--content", '[{"type":"text","text":"live verification"}]', "--full-comment"], identity="user"),
        Case("drive", "apply-permission", ["--token", doc, "--type", "docx", "--perm", "view", "--remark", "live verification"], identity="user", expect="blocked", note="owner applying to own doc may be rejected"),
        Case("drive", "export", ["--token", doc, "--doc-type", "docx", "--file-extension", "markdown", "--output-dir", str(r.out_dir), "--overwrite"], identity="user"),
        Case(
            "drive",
            "export-download",
            ["--file-token", "invalid_export_file_token", "--output-dir", str(r.out_dir), "--file-name", "export.bin", "--overwrite"],
            identity="user",
            expect="blocked",
            note="requires export file_token",
        ),
        Case("drive", "search", ["--query", "vv-live", "--page-size", "5"], identity="user"),
        Case("drive", "import", ["--file", file_path, "--type", "docx", "--folder-token", folder, "--name", f"import-{r.run_id}", "--poll-attempts", "1", "--poll-interval", "0"], identity="user"),
        Case("drive", "move", ["--file-token", file_token, "--type", "file", "--folder-token", folder], identity="user"),
        Case("drive", "task_result", ["--scenario", "task_check", "--task-id", "invalid_task_id"], identity="user", expect="blocked", note="requires async task id"),
        Case("drive", "requester-upload", [file_path], identity="user"),
        Case("calendar", "agenda", ["--calendar-id", "primary", "--start", "2026-05-01T00:00:00+08:00", "--end", "2026-05-02T00:00:00+08:00"], identity="user"),
        Case("calendar", "freebusy", ["--start", "2026-05-01T10:00:00+08:00", "--end", "2026-05-01T10:30:00+08:00", "--user-id", user], identity="user"),
        Case("calendar", "room-find", ["--slot", "2026-05-01T10:00:00+08:00~2026-05-01T10:30:00+08:00", "--min-capacity", "1"], identity="user"),
        Case("calendar", "suggestion", ["--start", "2026-05-01T10:00:00+08:00", "--end", "2026-05-01T11:00:00+08:00", "--duration-minutes", "15", "--attendee-ids", user], identity="user"),
        Case("calendar", "update", ["--calendar-id", "primary", "--event-id", event, "--summary", f"vv-live-updated-{r.run_id}"], identity="user"),
        Case("calendar", "attach-material", [file_path, "--calendar-id", "primary", "--event-id", event], identity="user"),
        Case("calendar", "rsvp", ["--calendar-id", "primary", "--event-id", event, "--rsvp-status", "accept"], identity="user"),
        Case("im", "chat-search", ["--query", "vv-live", "--page-size", "5"], identity="bot"),
        Case("im", "chat-update", ["--chat-id", chat, "--name", f"vv-live-updated-{r.run_id}"], identity="bot"),
        Case("im", "messages-send", ["--chat-id", chat, "--text", f"vv live {r.run_id}"], identity="bot"),
        Case("im", "chat-messages-list", ["--chat-id", chat, "--page-size", "5"], identity="bot"),
        Case("im", "messages-search", ["--query", "vv live", "--page-size", "5"], identity="bot"),
        Case("im", "messages-mget", ["--message-ids", "invalid_message_id"], identity="bot", expect="blocked", note="requires valid message_id"),
        Case("im", "messages-reply", ["--message-id", "invalid_message_id", "--text", "reply"], identity="bot", expect="blocked", note="requires valid message_id"),
        Case("im", "messages-resources-download", ["--message-id", "invalid_message_id", "--file-key", "invalid_file_key", "--output", str(r.out_dir)], identity="bot", expect="blocked", note="requires message resource"),
        Case("im", "threads-messages-list", ["--thread", "invalid_thread_id"], identity="bot", expect="blocked", note="requires valid thread id"),
        Case("sheets", "info", ["--spreadsheet-token", sheet], identity="user"),
        Case("sheets", "read", ["--spreadsheet-token", sheet, "--sheet-id", sid, "--range", "A1:B3"], identity="user"),
        Case("sheets", "write", ["--spreadsheet-token", sheet, "--sheet-id", sid, "--range", "A4:B4", "--values", '[["Carol",3]]'], identity="user"),
        Case("sheets", "append", ["--spreadsheet-token", sheet, "--sheet-id", sid, "--range", "A5:B5", "--values", '[["Dave",4]]'], identity="user"),
        Case("sheets", "find", ["--spreadsheet-token", sheet, "--sheet-id", sid, "--find", "Alice"], identity="user"),
        Case("sheets", "merge-cells", ["--spreadsheet-token", sheet, "--sheet-id", sid, "--range", "C1:D1"], identity="user"),
        Case("sheets", "unmerge-cells", ["--spreadsheet-token", sheet, "--sheet-id", sid, "--range", "C1:D1"], identity="user"),
        Case("sheets", "replace", ["--spreadsheet-token", sheet, "--sheet-id", sid, "--find", "Dave", "--replacement", "David"], identity="user"),
        Case("sheets", "set-style", ["--spreadsheet-token", sheet, "--sheet-id", sid, "--range", "A1:B1", "--style", '{"font":{"bold":true}}'], identity="user"),
        Case("sheets", "batch-set-style", ["--spreadsheet-token", sheet, "--data", f'[{{"ranges":["{sid}!A1:B1"],"style":{{"font":{{"bold":true}}}}}}]'], identity="user"),
        Case("sheets", "add-dimension", ["--spreadsheet-token", sheet, "--sheet-id", sid, "--dimension", "ROWS", "--length", "1"], identity="user"),
        Case("sheets", "insert-dimension", ["--spreadsheet-token", sheet, "--sheet-id", sid, "--dimension", "ROWS", "--start-index", "2", "--end-index", "3"], identity="user"),
        Case("sheets", "update-dimension", ["--spreadsheet-token", sheet, "--sheet-id", sid, "--dimension", "ROWS", "--start-index", "0", "--end-index", "1"], identity="user"),
        Case("sheets", "move-dimension", ["--spreadsheet-token", sheet, "--sheet-id", sid, "--dimension", "ROWS", "--source-index", "1", "--destination-index", "2", "--length", "1"], identity="user"),
        Case("sheets", "delete-dimension", ["--spreadsheet-token", sheet, "--sheet-id", sid, "--dimension", "ROWS", "--start-index", "9", "--end-index", "10"], identity="user", expect="blocked", note="range may be invalid in tiny fixture"),
        Case("sheets", "create-filter-view", ["--spreadsheet-token", sheet, "--sheet-id", sid, "--range", "A1:B10", "--filter-view-name", f"fv-{r.run_id}"], identity="user"),
        Case("sheets", "list-filter-views", ["--spreadsheet-token", sheet, "--sheet-id", sid], identity="user"),
        Case("sheets", "create-filter-view-condition", ["--spreadsheet-token", sheet, "--sheet-id", sid, "--filter-view-id", "invalid_filter_view", "--field-index", "0", "--expected", "Alice"], identity="user", expect="blocked", note="requires filter view id"),
        Case("sheets", "update-filter-view", ["--spreadsheet-token", sheet, "--sheet-id", sid, "--filter-view-id", "invalid_filter_view", "--range", "A1:B5"], identity="user", expect="blocked", note="requires filter view id"),
        Case("sheets", "get-filter-view", ["--spreadsheet-token", sheet, "--sheet-id", sid, "--filter-view-id", "invalid_filter_view"], identity="user", expect="blocked", note="requires filter view id"),
        Case("sheets", "delete-filter-view", ["--spreadsheet-token", sheet, "--sheet-id", sid, "--filter-view-id", "invalid_filter_view"], identity="user", expect="blocked", note="requires filter view id"),
        Case("sheets", "list-filter-view-conditions", ["--spreadsheet-token", sheet, "--sheet-id", sid, "--filter-view-id", "invalid_filter_view"], identity="user", expect="blocked", note="requires filter view id"),
        Case("sheets", "get-filter-view-condition", ["--spreadsheet-token", sheet, "--sheet-id", sid, "--filter-view-id", "invalid_filter_view", "--condition-id", "invalid_condition"], identity="user", expect="blocked"),
        Case("sheets", "update-filter-view-condition", ["--spreadsheet-token", sheet, "--sheet-id", sid, "--filter-view-id", "invalid_filter_view", "--condition-id", "invalid_condition", "--expected", "Alice"], identity="user", expect="blocked"),
        Case("sheets", "delete-filter-view-condition", ["--spreadsheet-token", sheet, "--sheet-id", sid, "--filter-view-id", "invalid_filter_view", "--condition-id", "invalid_condition"], identity="user", expect="blocked"),
        Case("sheets", "set-dropdown", ["--spreadsheet-token", sheet, "--range", f"{sid}!B2:B5", "--condition-values", '["Open","Closed"]'], identity="user"),
        Case("sheets", "get-dropdown", ["--spreadsheet-token", sheet, "--range", f"{sid}!B2:B5"], identity="user"),
        Case("sheets", "update-dropdown", ["--spreadsheet-token", sheet, "--sheet-id", sid, "--ranges", f'["{sid}!B2:B5"]', "--condition-values", '["Open"]'], identity="user"),
        Case("sheets", "delete-dropdown", ["--spreadsheet-token", sheet, "--ranges", f'["{sid}!B2:B5"]'], identity="user"),
        Case("sheets", "media-upload", ["--spreadsheet-token", sheet, "--sheet-id", sid, "--file", png_path], identity="user"),
        Case("sheets", "write-image", ["--spreadsheet-token", sheet, "--sheet-id", sid, "--file", png_path], identity="user"),
        Case("sheets", "list-float-images", ["--spreadsheet-token", sheet, "--sheet-id", sid], identity="user"),
        Case("sheets", "create-float-image", ["--spreadsheet-token", sheet, "--sheet-id", sid, "--float-image-token", "invalid_file_token", "--range", f"{sid}!A6:A6"], identity="user", expect="blocked", note="requires sheet image token"),
        Case("sheets", "get-float-image", ["--spreadsheet-token", sheet, "--sheet-id", sid, "--float-image-id", "invalid_image"], identity="user", expect="blocked"),
        Case("sheets", "update-float-image", ["--spreadsheet-token", sheet, "--sheet-id", sid, "--float-image-id", "invalid_image", "--range", f"{sid}!A6:A6"], identity="user", expect="blocked"),
        Case("sheets", "delete-float-image", ["--spreadsheet-token", sheet, "--sheet-id", sid, "--float-image-id", "invalid_image"], identity="user", expect="blocked"),
        Case("sheets", "export", ["--spreadsheet-token", sheet, "--file-extension", "xlsx"], identity="user"),
        Case("task", "comment", ["--task-id", task, "--content", "live comment"], identity="user"),
        Case("task", "complete", ["--task-id", task], identity="user"),
        Case("task", "reopen", ["--task-id", task], identity="user"),
        Case("task", "assign", ["--task-id", task, "--add", user], identity="user"),
        Case("task", "followers", ["--task-id", task, "--add", user], identity="user"),
        Case("task", "reminder", ["--task-id", task, "--set", "10m"], identity="user"),
        Case("task", "get-my-tasks", ["--query", "vv-live", "--page-limit", "1"], identity="user"),
        Case("task", "update", ["--task-id", task, "--summary", f"vv-live-updated-{r.run_id}"], identity="user"),
        Case("task", "set-ancestor", ["--task-id", child, "--ancestor-id", task], identity="user"),
        Case("task", "get-related-tasks", ["--task-id", task], identity="user"),
        Case("task", "search", ["--query", "vv-live"], identity="user"),
        Case("task", "subscribe-event", ["--resource-id", task, "--event-type", "task.updated"], identity="user"),
        Case("task", "tasklist-search", ["--query", "vv-live"], identity="user"),
        Case("task", "tasklist-task-add", ["--tasklist-id", tasklist, "--task-id", task], identity="user"),
        Case("task", "tasklist-members", ["--tasklist-id", tasklist, "--add", user], identity="user"),
        Case("mail", "triage", ["--mailbox", "me", "--max", "5"], identity="user"),
        Case("mail", "signature", ["--mailbox", "me"], identity="user"),
        Case("mail", "watch", ["--mailbox", "me"], identity="user"),
        Case("mail", "send", ["--mailbox", "me", "--to", "nobody@example.invalid", "--subject", f"vv-live-{r.run_id}", "--body", "draft only"], identity="user", expect="blocked", note="draft may be blocked by mailbox config"),
        Case("mail", "template-create", ["--mailbox", "me", "--name", f"vv-live-{r.run_id}", "--subject", "template", "--template-content", "hello"], identity="user", expect="blocked"),
        Case("mail", "message", ["--mailbox", "me", "--message-id", "invalid_message"], identity="user", expect="blocked"),
        Case("mail", "messages", ["--mailbox", "me", "--message-ids", "invalid_message"], identity="user", expect="blocked"),
        Case("mail", "reply", ["--mailbox", "me", "--message-id", "invalid_message", "--body", "reply"], identity="user", expect="blocked"),
        Case("mail", "reply-all", ["--mailbox", "me", "--message-id", "invalid_message", "--body", "reply"], identity="user", expect="blocked"),
        Case("mail", "forward", ["--mailbox", "me", "--message-id", "invalid_message", "--to", "nobody@example.invalid"], identity="user", expect="blocked"),
        Case("mail", "send-receipt", ["--mailbox", "me", "--message-id", "invalid_message"], identity="user", expect="blocked"),
        Case("mail", "decline-receipt", ["--mailbox", "me", "--message-id", "invalid_message"], identity="user", expect="blocked"),
        Case("mail", "share-to-chat", ["--mailbox", "me", "--message-id", "invalid_message", "--receive-id", chat], identity="user", expect="blocked"),
        Case("mail", "template-update", ["--mailbox", "me", "--template-id", "invalid_template", "--set-name", "updated"], identity="user", expect="blocked"),
        Case("mail", "draft-create", ["--user-mailbox-id", "me", "--raw", "Subject: vv live\\n\\nbody"], identity="user", expect="blocked"),
        Case("mail", "draft-edit", ["--user-mailbox-id", "me", "--draft-id", "invalid_draft", "--raw", "Subject: vv live\\n\\nbody"], identity="user", expect="blocked"),
        Case("mail", "thread", ["--user-mailbox-id", "me", "--thread-id", "invalid_thread"], identity="user", expect="blocked"),
        Case("mail", "send-markdown", ["--user-mailbox-id", "me", "--to-email", "nobody@example.invalid", "--subject", "vv live", "--markdown", "hello"], identity="user", expect="blocked"),
        Case("minutes", "search", ["--query", "vv", "--page-size", "5"], identity="user"),
        Case("minutes", "download", ["--minute-tokens", "invalid_minute"], identity="user", expect="blocked"),
        Case("vc", "search", ["--query", "vv", "--page-size", "5"], identity="user"),
        Case("vc", "notes", ["--meeting-ids", "invalid_meeting"], identity="user"),
        Case("vc", "recording", ["--meeting-ids", "invalid_meeting"], identity="user", expect="blocked", timeout=20, note="invalid meeting can be slow or rejected"),
        Case("okr", "cycle-list", ["--user-id", user], identity="user", expect="blocked"),
        Case("okr", "cycle-detail", ["--cycle-id", "invalid_cycle"], identity="user", expect="blocked"),
        Case("okr", "progress-list", ["--target-id", "invalid_target", "--target-type", "objective"], identity="user", expect="blocked"),
        Case("okr", "progress-get", ["--progress-id", "invalid_progress"], identity="user", expect="blocked"),
        Case("okr", "progress-create", ["--target-id", "invalid_target", "--target-type", "objective", "--content", '{"text":"live"}'], identity="user", expect="blocked"),
        Case("okr", "progress-update", ["--progress-id", "invalid_progress", "--target-type", "objective", "--content", '{"text":"live"}'], identity="user", expect="blocked"),
        Case("okr", "progress-delete", ["--progress-id", "invalid_progress"], identity="user", expect="blocked"),
        Case("okr", "upload-image", ["--target-id", "invalid_target", "--target-type", "objective", "--file", png_path], identity="user", expect="blocked"),
        Case("wiki", "node-create", ["--space-id", "my_library", "--title", f"vv-live-{r.run_id}", "--obj-type", "docx"], identity="user", note="depends on wiki personal library availability"),
        Case("wiki", "move", ["--obj-type", "docx", "--obj-token", doc, "--target-space-id", "my_library"], identity="user", note="depends on wiki target space"),
        Case("wiki", "delete-space", ["--space-id", "invalid_space", "--yes", "--poll-attempts", "1", "--poll-interval", "0"], identity="user", expect="blocked"),
        Case("whiteboard", "query", ["--whiteboard-token", "invalid_whiteboard"], identity="user", expect="blocked"),
        Case("whiteboard", "update", ["--whiteboard-token", "invalid_whiteboard", "--source", '{"raw_nodes":[]}', "--overwrite"], identity="user", expect="blocked"),
        Case("docs", "whiteboard-update", ["--whiteboard-token", "invalid_whiteboard", "--source", '{"raw_nodes":[]}', "--overwrite"], identity="user", expect="blocked"),
        Case("slides", "create", ["--title", f"vv-live-{r.run_id}", "--slides", '["<slide><title>Intro</title></slide>"]'], identity="user"),
        Case("slides", "media-upload", ["--presentation", "invalid_presentation", "--file", png_path], identity="user", expect="blocked"),
        Case("slides", "replace-slide", ["--presentation", "invalid_presentation", "--slide-id", "invalid_slide", "--parts", "[]"], identity="user", expect="blocked"),
        Case("docx", "convert-content", ["--content", "# Live", "--content-type", "markdown"], identity="user"),
        Case("docx", "insert-content", ["--document-id", doc, "--content", "# Inserted", "--content-type", "markdown"], identity="user"),
    ]
    for case in cases:
        payload = r.run_case(case)
        if case.key in {"wiki.+node-create", "wiki.+move"} and isinstance(payload, Mapping):
            item = wiki_created_item(payload, identity=case.identity)
            if item:
                r.created.append(item)

    bitable_payload = r.run_case(
        Case("bitable", "create-from-csv", [str(r.fixture_dir / "probe.csv"), "--app-name", f"vv-live-{r.run_id}", "--table-name", "Data"], identity="user")
    )
    if isinstance(bitable_payload, Mapping):
        app_token = str(bitable_payload.get("app_token") or "")
        if app_token:
            r.created.append({"type": "bitable", "token": app_token, "identity": "user"})


def run_base_cases(r: Runner) -> None:
    base_identity = "bot"
    base_payload = r.run_case(Case("base", "base-create", ["--name", f"vv-live-{r.run_id}"], identity=base_identity))
    base_token = str(base_payload.get("app", {}).get("app_token") if isinstance(base_payload.get("app"), Mapping) else base_payload.get("app_token") or base_payload.get("base_token") or "") if isinstance(base_payload, Mapping) else ""
    if base_token:
        r.created.append({"type": "bitable", "token": base_token, "identity": base_identity})
    if not base_token:
        r.record_manual(key="base.*", status="api_blocked", note="base-create did not return app token; running remaining base cases with placeholder", error_code="missing_fixture")
        base_token = "invalid_base_token"
    table_payload = r.run_case(Case("base", "table-create", ["--base-token", base_token, "--name", "Data"], identity=base_identity))
    table_id = first_prefixed_id(table_payload or {}, "tbl", "table_id", "id") if isinstance(table_payload, Mapping) else ""
    if not table_id:
        table_list = r.run_case(Case("base", "table-list", ["--base-token", base_token, "--limit", "10"], identity=base_identity))
        table_id = first_prefixed_id(table_list or {}, "tbl", "table_id", "id")
    if not table_id:
        table_id = "invalid_table_id"

    field_payload = r.run_case(Case("base", "field-create", ["--base-token", base_token, "--table-id", table_id, "--json", '{"name":"Status","type":"text"}'], identity=base_identity, expect="blocked", note="base field schema may vary"))
    field_id = first_item_id(field_payload or {}, "field_id", "id") or "invalid_field_id"
    view_payload = r.run_case(Case("base", "view-create", ["--base-token", base_token, "--table-id", table_id, "--json", '{"name":"Live View","type":"grid"}'], identity=base_identity, expect="blocked", note="base view schema may vary"))
    view_id = first_item_id(view_payload or {}, "view_id", "id") if isinstance(view_payload, Mapping) else ""
    if not view_id:
        view_list = r.run_case(Case("base", "view-list", ["--base-token", base_token, "--table-id", table_id], identity=base_identity))
        view_id = first_item_id(view_list or {}, "view_id", "id") or "invalid_view_id"
    record_payload = r.run_case(Case("base", "record-upsert", ["--base-token", base_token, "--table-id", table_id, "--json", '{"Status":"Open"}'], identity=base_identity, expect="blocked", note="depends on field schema"))
    record_id = first_item_id(record_payload or {}, "record_id", "id") if isinstance(record_payload, Mapping) else ""
    if not record_id:
        record_id = "invalid_record_id"

    cases = [
        Case("base", "base-get", ["--base-token", base_token], identity=base_identity),
        Case("base", "base-copy", ["--base-token", base_token, "--name", f"vv-live-copy-{r.run_id}", "--without-content"], identity=base_identity, expect="blocked"),
        Case("base", "table-list", ["--base-token", base_token], identity=base_identity),
        Case("base", "table-get", ["--base-token", base_token, "--table-id", table_id], identity=base_identity),
        Case("base", "table-update", ["--base-token", base_token, "--table-id", table_id, "--name", "Data Updated"], identity=base_identity),
        Case("base", "field-list", ["--base-token", base_token, "--table-id", table_id], identity=base_identity),
        Case("base", "field-get", ["--base-token", base_token, "--table-id", table_id, "--field-id", field_id], identity=base_identity, expect="blocked"),
        Case("base", "field-update", ["--base-token", base_token, "--table-id", table_id, "--field-id", field_id, "--json", '{"field_name":"Status2"}'], identity=base_identity, expect="blocked"),
        Case("base", "field-search-options", ["--base-token", base_token, "--table-id", table_id, "--field-id", field_id, "--keyword", "Open"], identity=base_identity, expect="blocked"),
        Case("base", "record-list", ["--base-token", base_token, "--table-id", table_id], identity=base_identity),
        Case("base", "record-search", ["--base-token", base_token, "--table-id", table_id, "--json", "{}"], identity=base_identity),
        Case("base", "record-get", ["--base-token", base_token, "--table-id", table_id, "--record-id", record_id], identity=base_identity, expect="blocked"),
        Case("base", "record-batch-create", ["--base-token", base_token, "--table-id", table_id, "--json", '{"fields":["Status"],"rows":[["Batch"]]}'], identity=base_identity, expect="blocked"),
        Case("base", "record-batch-update", ["--base-token", base_token, "--table-id", table_id, "--json", '{"records":[]}'], identity=base_identity, expect="blocked"),
        Case("base", "record-share-link-create", ["--base-token", base_token, "--table-id", table_id, "--record-ids", record_id], identity=base_identity, expect="blocked"),
        Case("base", "record-upload-attachment", ["--base-token", base_token, "--table-id", table_id, "--record-id", record_id, "--field-id", field_id, "--file", str(r.fixture_dir / "probe.txt")], identity=base_identity, expect="blocked"),
        Case("base", "record-history-list", ["--base-token", base_token, "--table-id", table_id, "--record-id", record_id], identity=base_identity, expect="blocked"),
        Case("base", "view-get", ["--base-token", base_token, "--table-id", table_id, "--view-id", view_id], identity=base_identity, expect="blocked"),
        Case("base", "view-get-filter", ["--base-token", base_token, "--table-id", table_id, "--view-id", view_id], identity=base_identity, expect="blocked"),
        Case("base", "view-set-filter", ["--base-token", base_token, "--table-id", table_id, "--view-id", view_id, "--json", "{}"], identity=base_identity, expect="blocked"),
        Case("base", "view-get-visible-fields", ["--base-token", base_token, "--table-id", table_id, "--view-id", view_id], identity=base_identity, expect="blocked"),
        Case("base", "view-set-visible-fields", ["--base-token", base_token, "--table-id", table_id, "--view-id", view_id, "--json", "[]"], identity=base_identity, expect="blocked"),
        Case("base", "view-get-group", ["--base-token", base_token, "--table-id", table_id, "--view-id", view_id], identity=base_identity, expect="blocked"),
        Case("base", "view-set-group", ["--base-token", base_token, "--table-id", table_id, "--view-id", view_id, "--json", '{"group_config":[]}'], identity=base_identity, expect="blocked"),
        Case("base", "view-get-sort", ["--base-token", base_token, "--table-id", table_id, "--view-id", view_id], identity=base_identity, expect="blocked"),
        Case("base", "view-set-sort", ["--base-token", base_token, "--table-id", table_id, "--view-id", view_id, "--json", "[]"], identity=base_identity, expect="blocked"),
        Case("base", "view-get-timebar", ["--base-token", base_token, "--table-id", table_id, "--view-id", view_id], identity=base_identity, expect="blocked"),
        Case("base", "view-set-timebar", ["--base-token", base_token, "--table-id", table_id, "--view-id", view_id, "--json", "{}"], identity=base_identity, expect="blocked"),
        Case("base", "view-get-card", ["--base-token", base_token, "--table-id", table_id, "--view-id", view_id], identity=base_identity, expect="blocked"),
        Case("base", "view-set-card", ["--base-token", base_token, "--table-id", table_id, "--view-id", view_id, "--json", "{}"], identity=base_identity, expect="blocked"),
        Case("base", "view-rename", ["--base-token", base_token, "--table-id", table_id, "--view-id", view_id, "--name", "Renamed"], identity=base_identity, expect="blocked"),
        Case("base", "role-list", ["--base-token", base_token], identity=base_identity),
        Case("base", "role-create", ["--base-token", base_token, "--json", '{"role_name":"Live Role"}'], identity=base_identity, expect="blocked"),
        Case("base", "role-get", ["--base-token", base_token, "--role-id", "invalid_role"], identity=base_identity, expect="blocked"),
        Case("base", "role-update", ["--base-token", base_token, "--role-id", "invalid_role", "--json", '{"role_name":"Updated"}'], identity=base_identity, expect="blocked"),
        Case("base", "role-delete", ["--base-token", base_token, "--role-id", "invalid_role"], identity=base_identity, expect="blocked"),
        Case("base", "advperm-enable", ["--base-token", base_token], identity=base_identity, expect="blocked"),
        Case("base", "advperm-disable", ["--base-token", base_token], identity=base_identity, expect="blocked"),
        Case("base", "workflow-list", ["--base-token", base_token], identity=base_identity),
        Case("base", "workflow-create", ["--base-token", base_token, "--json", '{"title":"Live Workflow","steps":[]}'], identity=base_identity, expect="blocked"),
        Case("base", "workflow-get", ["--base-token", base_token, "--workflow-id", "invalid_workflow"], identity=base_identity, expect="blocked"),
        Case("base", "workflow-update", ["--base-token", base_token, "--workflow-id", "invalid_workflow", "--json", '{"title":"Updated"}'], identity=base_identity, expect="blocked"),
        Case("base", "workflow-enable", ["--base-token", base_token, "--workflow-id", "invalid_workflow"], identity=base_identity, expect="blocked"),
        Case("base", "workflow-disable", ["--base-token", base_token, "--workflow-id", "invalid_workflow"], identity=base_identity, expect="blocked"),
        Case("base", "data-query", ["--base-token", base_token, "--dsl", "{}"], identity=base_identity, expect="blocked"),
        Case("base", "form-list", ["--base-token", base_token, "--table-id", table_id], identity=base_identity),
        Case("base", "form-create", ["--base-token", base_token, "--table-id", table_id, "--name", "Live Form"], identity=base_identity, expect="blocked"),
        Case("base", "form-get", ["--base-token", base_token, "--table-id", table_id, "--form-id", "invalid_form"], identity=base_identity, expect="blocked"),
        Case("base", "form-update", ["--base-token", base_token, "--table-id", table_id, "--form-id", "invalid_form", "--name", "Updated"], identity=base_identity, expect="blocked"),
        Case("base", "form-questions-list", ["--base-token", base_token, "--table-id", table_id, "--form-id", "invalid_form"], identity=base_identity, expect="blocked"),
        Case("base", "form-questions-create", ["--base-token", base_token, "--table-id", table_id, "--form-id", "invalid_form", "--questions", "[]"], identity=base_identity, expect="blocked"),
        Case("base", "form-questions-update", ["--base-token", base_token, "--table-id", table_id, "--form-id", "invalid_form", "--question-id", "invalid_question", "--json", "{}"], identity=base_identity, expect="blocked"),
        Case("base", "form-questions-delete", ["--base-token", base_token, "--table-id", table_id, "--form-id", "invalid_form", "--question-id", "invalid_question"], identity=base_identity, expect="blocked"),
        Case("base", "form-delete", ["--base-token", base_token, "--table-id", table_id, "--form-id", "invalid_form"], identity=base_identity, expect="blocked"),
        Case("base", "dashboard-list", ["--base-token", base_token], identity=base_identity),
        Case("base", "dashboard-create", ["--base-token", base_token, "--name", "Live Dashboard"], identity=base_identity, expect="blocked"),
        Case("base", "dashboard-get", ["--base-token", base_token, "--dashboard-id", "invalid_dashboard"], identity=base_identity, expect="blocked"),
        Case("base", "dashboard-update", ["--base-token", base_token, "--dashboard-id", "invalid_dashboard", "--name", "Updated"], identity=base_identity, expect="blocked"),
        Case("base", "dashboard-arrange", ["--base-token", base_token, "--dashboard-id", "invalid_dashboard", "--json", "{}"], identity=base_identity, expect="blocked"),
        Case("base", "dashboard-block-list", ["--base-token", base_token, "--dashboard-id", "invalid_dashboard"], identity=base_identity, expect="blocked"),
        Case("base", "dashboard-block-create", ["--base-token", base_token, "--dashboard-id", "invalid_dashboard", "--name", "Block", "--type", "chart"], identity=base_identity, expect="blocked"),
        Case("base", "dashboard-block-get", ["--base-token", base_token, "--dashboard-id", "invalid_dashboard", "--block-id", "invalid_block"], identity=base_identity, expect="blocked"),
        Case("base", "dashboard-block-update", ["--base-token", base_token, "--dashboard-id", "invalid_dashboard", "--block-id", "invalid_block", "--name", "Updated"], identity=base_identity, expect="blocked"),
        Case("base", "dashboard-block-delete", ["--base-token", base_token, "--dashboard-id", "invalid_dashboard", "--block-id", "invalid_block"], identity=base_identity, expect="blocked"),
        Case("base", "dashboard-delete", ["--base-token", base_token, "--dashboard-id", "invalid_dashboard"], identity=base_identity, expect="blocked"),
        Case("base", "field-delete", ["--base-token", base_token, "--table-id", table_id, "--field-id", field_id], identity=base_identity, expect="blocked"),
        Case("base", "view-delete", ["--base-token", base_token, "--table-id", table_id, "--view-id", view_id], identity=base_identity, expect="blocked"),
        Case("base", "record-delete", ["--base-token", base_token, "--table-id", table_id, "--record-id", record_id], identity=base_identity, expect="blocked"),
        Case("base", "table-delete", ["--base-token", base_token, "--table-id", table_id], identity=base_identity, expect="blocked"),
    ]
    for case in cases:
        payload = r.run_case(case)
        if case.key == "base.+base-copy" and isinstance(payload, Mapping):
            copied_token = str(payload.get("app_token") or payload.get("base_token") or "")
            if copied_token:
                r.created.append({"type": "bitable", "token": copied_token, "identity": base_identity})


def cleanup(r: Runner) -> None:
    cleaned_wiki_obj_tokens: set[str] = set()
    for item in reversed(r.created):
        token = item.get("token", "")
        typ = item.get("type", "")
        identity = item.get("identity", "user") or "user"
        if not token:
            continue
        if typ == "wiki_node":
            space_id = item.get("space_id", "")
            obj_type = item.get("obj_type", "")
            if not space_id or not obj_type:
                continue
            code, payload, raw, elapsed = r.raw_api(
                "DELETE",
                f"/wiki/v2/spaces/{quote(space_id, safe='')}/nodes/{quote(token, safe='')}",
                data={"obj_type": obj_type},
                identity=identity,
            )
            status = "pass" if code == 0 else "api_blocked"
            cleaned_wiki_obj_tokens.add(token)
            r.results.append(
                Result(
                    "wiki.node.delete.cleanup",
                    status,
                    code,
                    identity,
                    ["api", "DELETE"],
                    elapsed,
                    note="cleanup",
                    error_code=(payload.get("error", {}).get("code") if isinstance(payload, Mapping) and isinstance(payload.get("error"), Mapping) else None),
                    message=raw[:200],
                )
            )
            continue
        if typ == "task":
            r.run_case(Case("task", "delete", ["--task-id", token], identity="user", note="cleanup"))
        elif typ in {"file", "folder", "docx", "sheet", "bitable"}:
            if typ == "docx" and token in cleaned_wiki_obj_tokens:
                continue
            drive_type = {"file": "file", "folder": "folder", "docx": "docx", "sheet": "sheet", "bitable": "bitable"}[typ]
            r.run_case(Case("drive", "delete", ["--file-token", token, "--type", drive_type, "--yes"], identity=identity, note="cleanup", expect="blocked" if typ == "docx" else "pass"))
    event = r.ctx.get("event_id")
    if event:
        code, payload, raw, elapsed = r.raw_api("DELETE", f"/calendar/v4/calendars/primary/events/{event}", params={"need_notification": False}, identity="user")
        status = "pass" if code == 0 else "api_blocked"
        r.results.append(Result("calendar.events.delete.cleanup", status, code, "user", ["api", "DELETE"], elapsed, message=raw[:200]))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="")
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--no-cleanup", action="store_true")
    args = parser.parse_args()

    run_id = time.strftime("%Y%m%d%H%M%S")
    out_dir = Path(args.out_dir or f"/tmp/feishu-shortcut-live-{run_id}").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    env = build_env()
    if not env.get("FEISHU_APP_ID") or not env.get("FEISHU_APP_SECRET"):
        raise SystemExit("FEISHU_APP_ID/FEISHU_APP_SECRET or APP_ID/APP_SECRET required")
    runner = Runner(run_id=run_id, out_dir=out_dir, env=env, timeout=args.timeout)
    print(f"live verification output: {out_dir}", flush=True)
    create_core_fixtures(runner)
    run_base_cases(runner)
    run_general_cases(runner)
    if not args.no_cleanup:
        cleanup(runner)
    runner.save()
    print(json.dumps({"out_dir": str(out_dir), "summary": json.loads((out_dir / "live_verification_results.json").read_text())["summary"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
