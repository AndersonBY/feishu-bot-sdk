from __future__ import annotations

import json

from click.testing import CliRunner

from feishu_bot_sdk.cli.app import app


def test_schema_supports_lark_style_optional_path_for_method_and_service() -> None:
    runner = CliRunner()

    method = runner.invoke(app, ["schema", "drive.files.copy", "--format", "json"])
    assert method.exit_code == 0, method.output
    method_payload = json.loads(method.output)
    assert method_payload["id"] == "files.copy"
    assert method_payload["httpMethod"] == "POST"
    assert method_payload["path"] == "files/{file_token}/copy"

    service = runner.invoke(app, ["schema", "drive", "--format", "json"])
    assert service.exit_code == 0, service.output
    service_payload = json.loads(service.output)
    assert service_payload["name"] == "drive"
    assert "resources" in service_payload


def test_schema_pretty_marks_file_upload_methods() -> None:
    result = CliRunner().invoke(app, ["schema", "im.images.create", "--format", "pretty"])

    assert result.exit_code == 0, result.output
    assert "im.images.create" in result.output
    assert "file upload" in result.output
    assert "--file" in result.output
    assert 'Default field: \\"image\\"' in result.output


def test_schema_legacy_subcommands_still_work() -> None:
    runner = CliRunner()

    show = runner.invoke(app, ["schema", "show", "drive.files.copy", "--format", "json"])
    assert show.exit_code == 0, show.output
    show_payload = json.loads(show.output)
    assert show_payload["type"] == "service_method"

    paths = runner.invoke(app, ["schema", "paths", "--format", "json"])
    assert paths.exit_code == 0, paths.output
    paths_payload = json.loads(paths.output)
    assert "drive.files.copy" in paths_payload["items"]
