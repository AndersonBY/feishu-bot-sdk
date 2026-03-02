from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any

def _validate_positive_int(value: object, *, name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = int(value)
        except ValueError as exc:
            raise ValueError(f"{name} must be a positive integer") from exc
    else:
        raise ValueError(f"{name} must be a positive integer")
    if parsed <= 0:
        raise ValueError(f"{name} must be greater than 0")
    return parsed


def _validate_max_events(value: object) -> int | None:
    return _validate_positive_int(value, name="max-events")


def _validate_duration(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        parsed = float(value)
    elif isinstance(value, str):
        try:
            parsed = float(value)
        except ValueError as exc:
            raise ValueError("duration-seconds must be a positive number") from exc
    else:
        raise ValueError("duration-seconds must be a positive number")
    if parsed <= 0:
        raise ValueError("duration-seconds must be greater than 0")
    return parsed


def _resolve_output_path(path_value: object) -> Path | None:
    if not path_value:
        return None
    return Path(str(path_value))


def _resolve_pid_file(path_value: object) -> Path:
    if not path_value:
        return Path(".feishu_server.pid")
    return Path(str(path_value))


def _read_pid_file(pid_file: Path) -> int | None:
    if not pid_file.exists():
        return None
    text = pid_file.read_text(encoding="utf-8").strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _write_pid_file(pid_file: Path, pid: int) -> None:
    if pid_file.parent and not pid_file.parent.exists():
        pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(pid), encoding="utf-8")


def _remove_pid_file(pid_file: Path) -> None:
    if pid_file.exists():
        pid_file.unlink()


def _is_process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        completed = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            return False
        output = (completed.stdout or "").strip()
        if not output:
            return False
        if output.startswith("INFO:"):
            return False
        return str(pid) in output
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _terminate_process(pid: int) -> None:
    if os.name == "nt":
        completed = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"failed to stop process pid={pid}: {completed.stderr or completed.stdout}")
        return
    os.kill(pid, signal.SIGTERM)


def _build_server_run_subprocess_command(args: argparse.Namespace) -> list[str]:
    cmd = [
        sys.executable,
        "-m",
        "feishu_bot_sdk",
        "server",
        "run",
        "--format",
        "json",
    ]
    domain = getattr(args, "domain", None)
    if domain:
        cmd.extend(["--domain", str(domain)])
    if bool(getattr(args, "print_payload", False)):
        cmd.append("--print-payload")
    output_file = getattr(args, "output_file", None)
    if output_file:
        cmd.extend(["--output-file", str(output_file)])
    max_events = getattr(args, "max_events", None)
    if max_events is not None:
        cmd.extend(["--max-events", str(max_events)])
    for event_type in list(getattr(args, "event_types", []) or []):
        cmd.extend(["--event-type", str(event_type)])
    return cmd


def _spawn_background_process(cmd: list[str], *, log_file: object) -> subprocess.Popen[Any]:
    stdout_target: Any = subprocess.DEVNULL
    stderr_target: Any = subprocess.DEVNULL
    log_handle: Any = None
    if log_file:
        log_path = Path(str(log_file))
        if log_path.parent and not log_path.parent.exists():
            log_path.parent.mkdir(parents=True, exist_ok=True)
        log_handle = log_path.open("a", encoding="utf-8")
        stdout_target = log_handle
        stderr_target = log_handle

    popen_kwargs: dict[str, Any] = {
        "stdout": stdout_target,
        "stderr": stderr_target,
        "stdin": subprocess.DEVNULL,
        "close_fds": True,
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    else:
        popen_kwargs["start_new_session"] = True
    try:
        return subprocess.Popen(cmd, **popen_kwargs)
    finally:
        if log_handle is not None:
            log_handle.close()


def _normalize_server_path(path: str) -> str:
    if path.startswith("/"):
        return path
    return f"/{path}"


__all__ = [name for name in globals() if not name.startswith("__")]
