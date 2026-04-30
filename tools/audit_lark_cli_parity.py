from __future__ import annotations

import argparse
import importlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


SHORTCUT_DECL_RE = re.compile(
    r"Service:\s*\"(?P<service>[^\"]+)\"(?:(?!Service:).)*?Command:\s*\"(?P<command>\+[^\"]+)\"",
    re.DOTALL,
)


@dataclass(frozen=True)
class ParitySnapshot:
    shortcuts: set[str]
    services: set[str]
    service_methods: set[str]
    skills: set[str]
    top_level_commands: set[str]


@dataclass(frozen=True)
class MetadataFileDiff:
    required: set[str]
    present: set[str]
    missing: set[str]


@dataclass(frozen=True)
class ParityDiff:
    lark: ParitySnapshot
    feishu: ParitySnapshot
    missing_shortcuts: set[str]
    extra_shortcuts: set[str]
    common_shortcuts: set[str]
    missing_services: set[str]
    extra_services: set[str]
    missing_service_methods: set[str]
    extra_service_methods: set[str]
    missing_skills: set[str]
    extra_skills: set[str]
    missing_top_level_commands: set[str]
    extra_top_level_commands: set[str]
    metadata_files: MetadataFileDiff = field(
        default_factory=lambda: MetadataFileDiff(required=set(), present=set(), missing=set())
    )

    def missing_shortcuts_by_service(self) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = {}
        for item in sorted(self.missing_shortcuts):
            service, command = item.split(" ", 1)
            grouped.setdefault(service, []).append(command)
        return grouped


def parse_lark_shortcuts(lark_root: Path) -> set[str]:
    shortcuts_root = lark_root / "shortcuts"
    if not shortcuts_root.exists():
        return set()
    shortcuts: set[str] = set()
    for path in shortcuts_root.rglob("*.go"):
        if path.name.endswith("_test.go"):
            continue
        text = path.read_text(encoding="utf-8")
        for match in SHORTCUT_DECL_RE.finditer(text):
            shortcuts.add(f"{match.group('service')} {match.group('command')}")
    return shortcuts


def parse_lark_services(lark_root: Path) -> set[str]:
    meta_path = lark_root / "internal" / "registry" / "meta_data.json"
    if not meta_path.exists():
        return set()
    payload = json.loads(meta_path.read_text(encoding="utf-8"))
    services = payload.get("services", [])
    if not isinstance(services, list):
        return set()
    return {str(item.get("name")) for item in services if isinstance(item, dict) and item.get("name")}


def parse_lark_service_methods(lark_root: Path) -> set[str]:
    meta_path = lark_root / "internal" / "registry" / "meta_data.json"
    if not meta_path.exists():
        return set()
    payload = json.loads(meta_path.read_text(encoding="utf-8"))
    methods: set[str] = set()
    for service in payload.get("services", []):
        if not isinstance(service, dict):
            continue
        service_name = str(service.get("name") or "")
        resources = service.get("resources")
        if not service_name or not isinstance(resources, dict):
            continue
        for resource_name, resource in resources.items():
            if not isinstance(resource, dict):
                continue
            raw_methods = resource.get("methods")
            if not isinstance(raw_methods, dict):
                continue
            for method_name in raw_methods:
                methods.add(f"{service_name}.{resource_name}.{method_name}")
    return methods


def parse_lark_skills(lark_root: Path) -> set[str]:
    skills_root = lark_root / "skills"
    if not skills_root.exists():
        return set()
    return {path.parent.name for path in skills_root.glob("*/SKILL.md")}


def parse_lark_top_level_commands(lark_root: Path) -> set[str]:
    commands = {"api", "auth", "completion", "config", "doctor", "profile", "schema", "update", "event"}
    commands.update(parse_lark_services(lark_root))
    commands.update(item.split(" ", 1)[0] for item in parse_lark_shortcuts(lark_root))
    return commands


def parse_feishu_shortcuts(feishu_root: Path) -> set[str]:
    _ensure_import_path(feishu_root)
    shortcuts_module = importlib.import_module("feishu_bot_sdk.cli.shortcuts")
    return {f"{item.service} +{item.name}" for item in shortcuts_module.list_shortcuts()}


def parse_feishu_services(feishu_root: Path) -> set[str]:
    services_root = feishu_root / "src" / "feishu_bot_sdk" / "cli" / "metadata" / "services"
    if not services_root.exists():
        return set()
    return {path.stem for path in services_root.glob("*.json") if path.name != "__init__.py"}


def parse_feishu_service_methods(feishu_root: Path) -> set[str]:
    services_root = feishu_root / "src" / "feishu_bot_sdk" / "cli" / "metadata" / "services"
    if not services_root.exists():
        return set()
    methods: set[str] = set()
    for path in services_root.glob("*.json"):
        service = json.loads(path.read_text(encoding="utf-8"))
        service_name = str(service.get("name") or path.stem)
        resources = service.get("resources")
        if not isinstance(resources, dict):
            continue
        for resource_name, resource in resources.items():
            if not isinstance(resource, dict):
                continue
            raw_methods = resource.get("methods")
            if not isinstance(raw_methods, dict):
                continue
            for method_name in raw_methods:
                methods.add(f"{service_name}.{resource_name}.{method_name}")
    return methods


def parse_feishu_skills(feishu_root: Path) -> set[str]:
    skills_root = feishu_root / "skills"
    if not skills_root.exists():
        return set()
    return {path.parent.name for path in skills_root.glob("*/SKILL.md")}


def parse_feishu_top_level_commands(feishu_root: Path) -> set[str]:
    _ensure_import_path(feishu_root)
    app_module = importlib.import_module("feishu_bot_sdk.cli.app")
    return set(app_module.app.commands)


def build_snapshot(kind: str, root: Path) -> ParitySnapshot:
    if kind == "lark":
        return ParitySnapshot(
            shortcuts=parse_lark_shortcuts(root),
            services=parse_lark_services(root),
            service_methods=parse_lark_service_methods(root),
            skills=parse_lark_skills(root),
            top_level_commands=parse_lark_top_level_commands(root),
        )
    if kind == "feishu":
        return ParitySnapshot(
            shortcuts=parse_feishu_shortcuts(root),
            services=parse_feishu_services(root),
            service_methods=parse_feishu_service_methods(root),
            skills=parse_feishu_skills(root),
            top_level_commands=parse_feishu_top_level_commands(root),
        )
    raise ValueError(f"unknown snapshot kind: {kind}")


def compare_snapshots(lark: ParitySnapshot, feishu: ParitySnapshot) -> ParityDiff:
    return ParityDiff(
        lark=lark,
        feishu=feishu,
        missing_shortcuts=lark.shortcuts - feishu.shortcuts,
        extra_shortcuts=feishu.shortcuts - lark.shortcuts,
        common_shortcuts=lark.shortcuts & feishu.shortcuts,
        missing_services=lark.services - feishu.services,
        extra_services=feishu.services - lark.services,
        missing_service_methods=lark.service_methods - feishu.service_methods,
        extra_service_methods=feishu.service_methods - lark.service_methods,
        missing_skills=lark.skills - feishu.skills,
        extra_skills=feishu.skills - lark.skills,
        missing_top_level_commands=lark.top_level_commands - feishu.top_level_commands,
        extra_top_level_commands=feishu.top_level_commands - lark.top_level_commands,
    )


def build_diff(lark_root: Path, feishu_root: Path) -> ParityDiff:
    diff = compare_snapshots(build_snapshot("lark", lark_root), build_snapshot("feishu", feishu_root))
    return ParityDiff(
        lark=diff.lark,
        feishu=diff.feishu,
        missing_shortcuts=diff.missing_shortcuts,
        extra_shortcuts=diff.extra_shortcuts,
        common_shortcuts=diff.common_shortcuts,
        missing_services=diff.missing_services,
        extra_services=diff.extra_services,
        missing_service_methods=diff.missing_service_methods,
        extra_service_methods=diff.extra_service_methods,
        missing_skills=diff.missing_skills,
        extra_skills=diff.extra_skills,
        missing_top_level_commands=diff.missing_top_level_commands,
        extra_top_level_commands=diff.extra_top_level_commands,
        metadata_files=find_required_metadata_files(lark_root, feishu_root),
    )


def find_required_metadata_files(lark_root: Path, feishu_root: Path) -> MetadataFileDiff:
    required = {
        "metadata/meta_version.json",
        "metadata/scope_overrides.json",
        "metadata/scope_priorities.json",
        "metadata/service_descriptions.json",
    }
    required.update(f"metadata/services/{service}.json" for service in parse_lark_services(lark_root))
    if (lark_root / "internal" / "event" / "schemas").exists():
        required.add("metadata/events/schemas.json")

    metadata_root = feishu_root / "src" / "feishu_bot_sdk" / "cli" / "metadata"
    present = {item for item in required if (metadata_root / item.removeprefix("metadata/")).is_file()}
    return MetadataFileDiff(required=required, present=present, missing=required - present)


def render_markdown_report(diff: ParityDiff) -> str:
    lines = [
        "# lark-cli Parity Report",
        "",
        "## Summary",
        "",
        "| Area | lark-cli | feishu-bot-sdk | Missing |",
        "|---|---:|---:|---:|",
        f"| Shortcuts | {len(diff.lark.shortcuts)} | {len(diff.feishu.shortcuts)} | {len(diff.missing_shortcuts)} |",
        f"| Services | {len(diff.lark.services)} | {len(diff.feishu.services)} | {len(diff.missing_services)} |",
        f"| Service methods | {len(diff.lark.service_methods)} | {len(diff.feishu.service_methods)} | {len(diff.missing_service_methods)} |",
        f"| Skills | {len(diff.lark.skills)} | {len(diff.feishu.skills)} | {len(diff.missing_skills)} |",
        f"| Top-level commands | {len(diff.lark.top_level_commands)} | {len(diff.feishu.top_level_commands)} | {len(diff.missing_top_level_commands)} |",
        f"| Required metadata files | {len(diff.metadata_files.required)} | {len(diff.metadata_files.present)} | {len(diff.metadata_files.missing)} |",
        "",
        "## Missing Shortcuts By Service",
        "",
        "| Service | Missing count | Commands |",
        "|---|---:|---|",
    ]
    grouped = diff.missing_shortcuts_by_service()
    if grouped:
        for service, commands in grouped.items():
            rendered = ", ".join(f"`{command}`" for command in commands)
            lines.append(f"| {service} | {len(commands)} | {rendered} |")
    else:
        lines.append("| none | 0 |  |")
    if diff.extra_shortcuts:
        lines.extend(["", "## Extra feishu-bot-sdk Shortcuts", ""])
        lines.extend(f"- `{item}`" for item in sorted(diff.extra_shortcuts))
    if diff.missing_services:
        lines.extend(["", "## Missing Services", ""])
        lines.extend(f"- `{item}`" for item in sorted(diff.missing_services))
    if diff.missing_service_methods:
        lines.extend(["", "## Missing Service Methods", ""])
        lines.extend(f"- `{item}`" for item in sorted(diff.missing_service_methods))
    if diff.missing_skills:
        lines.extend(["", "## Missing Skills", ""])
        lines.extend(f"- `{item}`" for item in sorted(diff.missing_skills))
    if diff.missing_top_level_commands:
        lines.extend(["", "## Missing Top-Level Commands", ""])
        lines.extend(f"- `{item}`" for item in sorted(diff.missing_top_level_commands))
    if diff.metadata_files.missing:
        lines.extend(["", "## Missing Required Metadata Files", ""])
        lines.extend(f"- `{item}`" for item in sorted(diff.metadata_files.missing))
    return "\n".join(lines) + "\n"


def diff_to_jsonable(diff: ParityDiff) -> dict[str, object]:
    return {
        "summary": {
            "lark_shortcuts": len(diff.lark.shortcuts),
            "feishu_shortcuts": len(diff.feishu.shortcuts),
            "missing_shortcuts": len(diff.missing_shortcuts),
            "lark_services": len(diff.lark.services),
            "feishu_services": len(diff.feishu.services),
            "missing_services": len(diff.missing_services),
            "lark_service_methods": len(diff.lark.service_methods),
            "feishu_service_methods": len(diff.feishu.service_methods),
            "missing_service_methods": len(diff.missing_service_methods),
            "lark_skills": len(diff.lark.skills),
            "feishu_skills": len(diff.feishu.skills),
            "missing_skills": len(diff.missing_skills),
            "lark_top_level_commands": len(diff.lark.top_level_commands),
            "feishu_top_level_commands": len(diff.feishu.top_level_commands),
            "missing_top_level_commands": len(diff.missing_top_level_commands),
            "required_metadata_files": len(diff.metadata_files.required),
            "present_metadata_files": len(diff.metadata_files.present),
            "missing_metadata_files": len(diff.metadata_files.missing),
        },
        "missing_shortcuts": sorted(diff.missing_shortcuts),
        "missing_shortcuts_by_service": diff.missing_shortcuts_by_service(),
        "extra_shortcuts": sorted(diff.extra_shortcuts),
        "common_shortcuts": sorted(diff.common_shortcuts),
        "missing_services": sorted(diff.missing_services),
        "extra_services": sorted(diff.extra_services),
        "missing_service_methods": sorted(diff.missing_service_methods),
        "extra_service_methods": sorted(diff.extra_service_methods),
        "missing_skills": sorted(diff.missing_skills),
        "extra_skills": sorted(diff.extra_skills),
        "missing_top_level_commands": sorted(diff.missing_top_level_commands),
        "extra_top_level_commands": sorted(diff.extra_top_level_commands),
        "missing_metadata_files": sorted(diff.metadata_files.missing),
        "required_metadata_files": sorted(diff.metadata_files.required),
    }


def _ensure_import_path(feishu_root: Path) -> None:
    import sys

    src = feishu_root / "src"
    root = str(src if src.exists() else feishu_root)
    if root not in sys.path:
        sys.path.insert(0, root)


def _filter_domain(items: Iterable[str], domain: str | None) -> set[str]:
    if not domain:
        return set(items)
    prefix = f"{domain} "
    return {item for item in items if item.startswith(prefix)}


def filter_diff(diff: ParityDiff, domain: str | None) -> ParityDiff:
    if not domain:
        return diff
    lark = ParitySnapshot(
        shortcuts=_filter_domain(diff.lark.shortcuts, domain),
        services={domain} if domain in diff.lark.services else set(),
        service_methods=_filter_domain(diff.lark.service_methods, domain),
        skills={item for item in diff.lark.skills if item == f"lark-{domain}"},
        top_level_commands={domain} if domain in diff.lark.top_level_commands else set(),
    )
    feishu = ParitySnapshot(
        shortcuts=_filter_domain(diff.feishu.shortcuts, domain),
        services={domain} if domain in diff.feishu.services else set(),
        service_methods=_filter_domain(diff.feishu.service_methods, domain),
        skills={item for item in diff.feishu.skills if item in {domain, f"lark-{domain}"}},
        top_level_commands={domain} if domain in diff.feishu.top_level_commands else set(),
    )
    filtered = compare_snapshots(lark, feishu)
    return ParityDiff(
        lark=filtered.lark,
        feishu=filtered.feishu,
        missing_shortcuts=filtered.missing_shortcuts,
        extra_shortcuts=filtered.extra_shortcuts,
        common_shortcuts=filtered.common_shortcuts,
        missing_services=filtered.missing_services,
        extra_services=filtered.extra_services,
        missing_service_methods=filtered.missing_service_methods,
        extra_service_methods=filtered.extra_service_methods,
        missing_skills=filtered.missing_skills,
        extra_skills=filtered.extra_skills,
        missing_top_level_commands=filtered.missing_top_level_commands,
        extra_top_level_commands=filtered.extra_top_level_commands,
        metadata_files=diff.metadata_files,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit feishu-bot-sdk CLI parity against lark-cli")
    parser.add_argument("--source", default="../lark-cli", help="Path to lark-cli checkout")
    parser.add_argument("--target", default=".", help="Path to feishu-bot-sdk checkout")
    parser.add_argument("--domain", help="Limit shortcut/service comparison to one domain")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", help="Write report to a file")
    parser.add_argument("--fail-on-missing", action="store_true", help="Exit non-zero when required parity is missing")
    args = parser.parse_args(argv)

    diff = filter_diff(build_diff(Path(args.source), Path(args.target)), args.domain)
    if args.format == "json":
        output = json.dumps(diff_to_jsonable(diff), ensure_ascii=False, indent=2) + "\n"
    else:
        output = render_markdown_report(diff)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output, end="")

    if args.fail_on_missing and (
        diff.missing_shortcuts
        or diff.missing_services
        or diff.missing_service_methods
        or diff.missing_top_level_commands
        or diff.metadata_files.missing
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
