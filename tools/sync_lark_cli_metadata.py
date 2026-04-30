from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


METADATA_ROOT = Path("src/feishu_bot_sdk/cli/metadata")
COPY_FILES = ("scope_overrides.json", "scope_priorities.json", "service_descriptions.json")


@dataclass(frozen=True)
class SyncSummary:
    changed: bool
    service_count: int
    would_change: list[str]
    source_commit: str


def sync_metadata(
    source_root: Path,
    target_root: Path,
    *,
    source_commit: str | None = None,
    check: bool = False,
) -> SyncSummary:
    registry_root = source_root / "internal" / "registry"
    meta_path = registry_root / "meta_data.json"
    payload = json.loads(meta_path.read_text(encoding="utf-8"))
    services = payload.get("services", [])
    if not isinstance(services, list):
        raise ValueError("lark-cli meta_data.json must contain a services list")

    commit = source_commit or resolve_source_commit(source_root)
    writes: dict[Path, str] = {}
    metadata_root = target_root / METADATA_ROOT
    services_root = metadata_root / "services"

    for service in sorted(services, key=lambda item: str(item.get("name", ""))):
        if not isinstance(service, dict):
            continue
        name = service.get("name")
        if not name:
            raise ValueError("service metadata item missing name")
        writes[services_root / f"{name}.json"] = _json_dumps(service)

    meta_version = {
        "version": str(payload.get("version") or ""),
        "service_count": len(writes),
        "source": "lark-cli",
        "source_commit": commit,
    }
    writes[metadata_root / "meta_version.json"] = _json_dumps(meta_version)

    for filename in COPY_FILES:
        source_file = registry_root / filename
        if source_file.exists():
            writes[metadata_root / filename] = source_file.read_text(encoding="utf-8")

    changed_paths = [path for path, content in writes.items() if _read_existing(path) != content]
    if not check:
        for path, content in writes.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    return SyncSummary(
        changed=bool(changed_paths),
        service_count=len(writes) - 1 - sum(1 for filename in COPY_FILES if (registry_root / filename).exists()),
        would_change=sorted(str(path.relative_to(target_root)) for path in changed_paths),
        source_commit=commit,
    )


def resolve_source_commit(source_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(source_root), "rev-parse", "--short", "HEAD"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def _read_existing(path: Path) -> str | None:
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync lark-cli metadata into feishu-bot-sdk")
    parser.add_argument("--source", default="../lark-cli", help="Path to lark-cli checkout")
    parser.add_argument("--target", default=".", help="Path to feishu-bot-sdk checkout")
    parser.add_argument("--source-commit", help="Override source commit recorded in meta_version.json")
    parser.add_argument("--check", action="store_true", help="Report pending changes without writing")
    args = parser.parse_args(argv)

    summary = sync_metadata(
        Path(args.source),
        Path(args.target),
        source_commit=args.source_commit,
        check=args.check,
    )
    print(
        json.dumps(
            {
                "changed": summary.changed,
                "service_count": summary.service_count,
                "would_change": summary.would_change,
                "source_commit": summary.source_commit,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 1 if args.check and summary.changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
