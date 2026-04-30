from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import feishu_bot_sdk.cli as cli
from feishu_bot_sdk.cli.runtime import load_cli_config


def _configure_cli_paths(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setenv("FEISHU_CLI_CONFIG_PATH", str(tmp_path / "config" / "cli-config.json"))
    monkeypatch.setenv("FEISHU_SECRET_STORE_PATH", str(tmp_path / "config" / "cli-secrets.json"))
    monkeypatch.setenv("FEISHU_SECRET_STORE_KEY_PATH", str(tmp_path / "config" / "cli-secrets.key"))
    monkeypatch.setenv("FEISHU_SECRET_STORE_BACKEND", "encrypted_file")
    monkeypatch.delenv("FEISHU_PROFILE", raising=False)


def test_config_strict_mode_view_set_global_and_reset(
    monkeypatch: Any,
    tmp_path: Path,
    capsys: Any,
) -> None:
    _configure_cli_paths(monkeypatch, tmp_path)
    assert (
        cli.main(
            [
                "config",
                "init",
                "--profile",
                "work",
                "--app-id",
                "cli_work",
                "--app-secret",
                "secret",
                "--set-default",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()

    code = cli.main(["config", "strict-mode", "--format", "json"])
    assert code == 0
    show_payload = json.loads(capsys.readouterr().out)
    assert show_payload["strict_mode"] == "off"
    assert show_payload["source"] == "global_default"

    code = cli.main(["config", "strict-mode", "bot", "--global", "--format", "json"])
    assert code == 0
    global_payload = json.loads(capsys.readouterr().out)
    assert global_payload["strict_mode"] == "bot"
    assert global_payload["scope"] == "global"
    assert load_cli_config().strict_mode == "bot"

    code = cli.main(["config", "strict-mode", "user", "--profile", "work", "--format", "json"])
    assert code == 0
    profile_payload = json.loads(capsys.readouterr().out)
    assert profile_payload["strict_mode"] == "user"
    assert profile_payload["scope"] == "profile"
    assert load_cli_config().profile("work").strict_mode == "user"  # type: ignore[union-attr]

    code = cli.main(["config", "strict-mode", "--reset", "--profile", "work", "--format", "json"])
    assert code == 0
    reset_payload = json.loads(capsys.readouterr().out)
    assert reset_payload["strict_mode"] == "bot"
    assert reset_payload["source"] == "global"
    assert load_cli_config().profile("work").strict_mode is None  # type: ignore[union-attr]


def test_config_bind_records_agent_binding_without_claiming_secret_sync(
    monkeypatch: Any,
    tmp_path: Path,
    capsys: Any,
) -> None:
    _configure_cli_paths(monkeypatch, tmp_path)

    code = cli.main(
        [
            "config",
            "bind",
            "--source",
            "openclaw",
            "--app-id",
            "cli_bound",
            "--identity",
            "bot-only",
            "--force",
            "--lang",
            "en",
            "--format",
            "json",
        ]
    )
    assert code == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["source"] == "openclaw"
    assert payload["app_id"] == "cli_bound"
    assert payload["identity"] == "bot-only"
    assert payload["default_as"] == "bot"
    assert payload["strict_mode"] == "bot"
    assert payload["credentials_synced"] is False
    assert payload["profile"] == "openclaw"

    config = load_cli_config()
    assert config.default_profile == "openclaw"
    profile = config.profile("openclaw")
    assert profile is not None
    assert profile.app_id == "cli_bound"
    assert profile.default_as == "bot"
    assert profile.strict_mode == "bot"
    assert profile.binding is not None
    assert profile.binding["source"] == "openclaw"

