from __future__ import annotations

import json
from pathlib import Path

from tools.audit_lark_cli_parity import (
    ParitySnapshot,
    compare_snapshots,
    find_required_metadata_files,
    parse_feishu_shortcuts,
    parse_lark_shortcuts,
    render_markdown_report,
)


def test_parse_lark_shortcuts_reads_production_go_shortcut_declarations(tmp_path: Path) -> None:
    shortcuts_dir = tmp_path / "shortcuts" / "calendar"
    shortcuts_dir.mkdir(parents=True)
    (shortcuts_dir / "calendar_agenda.go").write_text(
        '''
package calendar

import "github.com/larksuite/cli/shortcuts/common"

var CalendarAgenda = common.Shortcut{
    Service:     "calendar",
    Command:     "+agenda",
    Description: "show agenda",
}
''',
        encoding="utf-8",
    )
    (shortcuts_dir / "calendar_test.go").write_text(
        '''
package calendar

import "github.com/larksuite/cli/shortcuts/common"

var TestShortcut = common.Shortcut{
    Service: "calendar",
    Command: "+test-only",
}
''',
        encoding="utf-8",
    )

    assert parse_lark_shortcuts(tmp_path) == {"calendar +agenda"}


def test_parse_feishu_shortcuts_reads_current_python_registry() -> None:
    shortcuts = parse_feishu_shortcuts(Path.cwd())

    assert "drive +export" in shortcuts
    assert "task +create" in shortcuts
    assert "calendar +rsvp" in shortcuts


def test_compare_snapshots_reports_missing_extra_and_common_by_domain() -> None:
    lark = ParitySnapshot(
        shortcuts={"drive +upload", "drive +export", "mail +send"},
        services={"drive", "mail"},
        service_methods={"drive.files.copy", "mail.messages.get"},
        skills={"lark-drive", "lark-mail"},
        top_level_commands={"drive", "mail", "update"},
    )
    feishu = ParitySnapshot(
        shortcuts={"drive +export", "mail +send-markdown"},
        services={"drive"},
        service_methods={"drive.files.copy"},
        skills={"feishu"},
        top_level_commands={"drive"},
    )

    diff = compare_snapshots(lark, feishu)

    assert diff.missing_shortcuts == {"drive +upload", "mail +send"}
    assert diff.extra_shortcuts == {"mail +send-markdown"}
    assert diff.common_shortcuts == {"drive +export"}
    assert diff.missing_services == {"mail"}
    assert diff.missing_service_methods == {"mail.messages.get"}
    assert diff.missing_skills == {"lark-drive", "lark-mail"}
    assert diff.missing_top_level_commands == {"mail", "update"}
    assert diff.missing_shortcuts_by_service() == {
        "drive": ["+upload"],
        "mail": ["+send"],
    }


def test_render_markdown_report_includes_counts_and_domain_rows() -> None:
    diff = compare_snapshots(
        ParitySnapshot(
            shortcuts={"drive +upload", "drive +export"},
            services={"drive"},
            service_methods={"drive.files.copy"},
            skills={"lark-drive"},
            top_level_commands={"drive"},
        ),
        ParitySnapshot(
            shortcuts={"drive +export"},
            services={"drive"},
            service_methods={"drive.files.copy"},
            skills={"lark-drive"},
            top_level_commands={"drive"},
        ),
    )

    report = render_markdown_report(diff)

    assert "# lark-cli Parity Report" in report
    assert "| Shortcuts | 2 | 1 | 1 |" in report
    assert "| drive | 1 | `+upload` |" in report


def test_required_metadata_files_include_service_and_event_schema_snapshots(tmp_path: Path) -> None:
    lark_root = tmp_path / "lark-cli"
    feishu_root = tmp_path / "feishu"
    (lark_root / "internal" / "registry").mkdir(parents=True)
    (lark_root / "internal" / "registry" / "meta_data.json").write_text(
        json.dumps({"services": [{"name": "drive", "resources": {}}]}),
        encoding="utf-8",
    )
    (lark_root / "internal" / "registry" / "scope_overrides.json").write_text("{}", encoding="utf-8")
    (lark_root / "internal" / "registry" / "scope_priorities.json").write_text("[]", encoding="utf-8")
    (lark_root / "internal" / "registry" / "service_descriptions.json").write_text("{}", encoding="utf-8")
    (lark_root / "internal" / "event" / "schemas").mkdir(parents=True)
    (lark_root / "internal" / "event" / "schemas" / "envelope.go").write_text("package schemas", encoding="utf-8")

    required = find_required_metadata_files(lark_root, feishu_root)

    assert required.required == {
        "metadata/events/schemas.json",
        "metadata/meta_version.json",
        "metadata/scope_overrides.json",
        "metadata/scope_priorities.json",
        "metadata/service_descriptions.json",
        "metadata/services/drive.json",
    }
    assert required.missing == required.required


def test_cli_json_output_lists_missing_shortcuts(tmp_path: Path) -> None:
    lark_root = tmp_path / "lark-cli"
    feishu_root = tmp_path / "feishu"
    (lark_root / "shortcuts" / "drive").mkdir(parents=True)
    (feishu_root / "src" / "feishu_bot_sdk" / "cli" / "metadata" / "services").mkdir(parents=True)
    (lark_root / "shortcuts" / "drive" / "drive_fixture_missing.go").write_text(
        'package drive\nimport "github.com/larksuite/cli/shortcuts/common"\n'
        'var DriveFixtureMissing = common.Shortcut{Service: "drive", Command: "+fixture-missing"}\n',
        encoding="utf-8",
    )
    (feishu_root / "src" / "feishu_bot_sdk" / "cli" / "metadata" / "services" / "drive.json").write_text(
        json.dumps({"name": "drive", "resources": {}}),
        encoding="utf-8",
    )

    from tools.audit_lark_cli_parity import build_diff

    diff = build_diff(lark_root, feishu_root)
    assert diff.missing_shortcuts == {"drive +fixture-missing"}
