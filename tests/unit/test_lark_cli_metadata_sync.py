from __future__ import annotations

import json
from pathlib import Path

from tools.sync_lark_cli_metadata import sync_metadata


def test_sync_metadata_splits_lark_registry_services_and_records_source_commit(tmp_path: Path) -> None:
    source = tmp_path / "lark-cli"
    registry = source / "internal" / "registry"
    registry.mkdir(parents=True)
    (registry / "meta_data.json").write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "services": [
                    {
                        "name": "drive",
                        "title": "Drive",
                        "description": "Drive API",
                        "servicePath": "/open-apis/drive/v1",
                        "resources": {"files": {"methods": {}}},
                    },
                    {
                        "name": "calendar",
                        "title": "Calendar",
                        "description": "Calendar API",
                        "servicePath": "/open-apis/calendar/v4",
                        "resources": {"events": {"methods": {}}},
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    (registry / "scope_overrides.json").write_text('{"recommend": {"allow": ["drive:file:upload"]}}', encoding="utf-8")
    (registry / "scope_priorities.json").write_text('[{"scope_name": "drive:file:upload"}]', encoding="utf-8")
    (registry / "service_descriptions.json").write_text('{"drive": {"en": {"title": "Drive"}}}', encoding="utf-8")

    target = tmp_path / "feishu"

    summary = sync_metadata(source, target, source_commit="abc1234", check=False)

    assert summary.changed is True
    assert summary.service_count == 2
    assert (target / "src/feishu_bot_sdk/cli/metadata/services/calendar.json").exists()
    drive_payload = json.loads(
        (target / "src/feishu_bot_sdk/cli/metadata/services/drive.json").read_text(encoding="utf-8")
    )
    assert drive_payload["name"] == "drive"
    assert drive_payload["servicePath"] == "/open-apis/drive/v1"
    meta_version = json.loads(
        (target / "src/feishu_bot_sdk/cli/metadata/meta_version.json").read_text(encoding="utf-8")
    )
    assert meta_version == {
        "version": "1.0.0",
        "service_count": 2,
        "source": "lark-cli",
        "source_commit": "abc1234",
    }
    assert (target / "src/feishu_bot_sdk/cli/metadata/service_descriptions.json").exists()


def test_sync_metadata_check_mode_reports_pending_changes_without_writing(tmp_path: Path) -> None:
    source = tmp_path / "lark-cli"
    registry = source / "internal" / "registry"
    registry.mkdir(parents=True)
    (registry / "meta_data.json").write_text(
        json.dumps({"version": "1.0.0", "services": [{"name": "drive", "resources": {}}]}),
        encoding="utf-8",
    )

    target = tmp_path / "feishu"

    summary = sync_metadata(source, target, source_commit="abc1234", check=True)

    assert summary.changed is True
    assert summary.would_change == [
        "src/feishu_bot_sdk/cli/metadata/meta_version.json",
        "src/feishu_bot_sdk/cli/metadata/services/drive.json",
    ]
    assert not (target / "src").exists()

