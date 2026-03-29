from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
from typing import Any

import feishu_bot_sdk.cli as cli
from feishu_bot_sdk.cli.runtime import (
    _resolve_user_token_store_context,
    list_cli_profiles,
    load_cli_config,
    resolve_cli_profile,
    resolve_secret_store,
)


_CLEARED_ENV_KEYS = (
    "APP_ID",
    "APP_SECRET",
    "FEISHU_APP_ACCESS_TOKEN",
    "FEISHU_APP_ID",
    "FEISHU_APP_SECRET",
    "FEISHU_AUTH_MODE",
    "FEISHU_BASE_URL",
    "FEISHU_NO_STORE",
    "FEISHU_PROFILE",
    "FEISHU_SECRET_STORE_BACKEND",
    "FEISHU_TIMEOUT_SECONDS",
    "FEISHU_TOKEN_STORE",
    "FEISHU_TOKEN_STORE_PATH",
    "FEISHU_USER_ACCESS_TOKEN",
    "FEISHU_USER_REFRESH_TOKEN",
)


def _configure_cli_paths(monkeypatch: Any, tmp_path: Path) -> tuple[Path, Path, Path]:
    config_path = tmp_path / "config" / "cli-config.json"
    secret_store_path = tmp_path / "config" / "cli-secrets.json"
    secret_key_path = tmp_path / "config" / "cli-secrets.key"
    monkeypatch.setenv("FEISHU_CLI_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("FEISHU_SECRET_STORE_PATH", str(secret_store_path))
    monkeypatch.setenv("FEISHU_SECRET_STORE_KEY_PATH", str(secret_key_path))
    for key in _CLEARED_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    return config_path, secret_store_path, secret_key_path


def _auth_args(profile: str, **overrides: Any) -> argparse.Namespace:
    data: dict[str, Any] = {
        "access_token": None,
        "app_access_token": None,
        "app_id": None,
        "app_secret": None,
        "auth_command": "",
        "auth_mode": None,
        "base_url": None,
        "group": None,
        "no_store": False,
        "oauth_command": "",
        "profile": profile,
        "timeout": None,
        "token_store": None,
        "user_access_token": None,
        "user_refresh_token": None,
    }
    data.update(overrides)
    return argparse.Namespace(**data)


def test_config_commands_store_profile_and_encrypt_secret(
    monkeypatch: Any, tmp_path: Path, capsys: Any
) -> None:
    config_path, secret_store_path, secret_key_path = _configure_cli_paths(monkeypatch, tmp_path)
    token_store_path = tmp_path / "tokens" / "work.json"
    monkeypatch.setattr("sys.stdin", io.StringIO("work-secret-value"))

    code = cli.main(
        [
            "config",
            "init",
            "--profile",
            "work",
            "--app-id",
            "cli_work",
            "--app-secret-stdin",
            "--auth-mode",
            "auto",
            "--base-url",
            "https://open.example.test/open-apis",
            "--timeout",
            "45",
            "--token-store",
            str(token_store_path),
            "--set-default",
            "--format",
            "json",
        ]
    )
    assert code == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "work"
    assert payload["default"] is True
    assert payload["default_profile"] == "work"
    assert payload["app_id"] == "cli_work"
    assert payload["auth_mode"] == "auto"
    assert payload["base_url"] == "https://open.example.test/open-apis"
    assert payload["timeout_seconds"] == 45.0
    assert payload["token_store_path"] == str(token_store_path)
    assert payload["has_app_secret"] is True
    assert payload["config_path"] == str(config_path)
    assert payload["secret_store_path"] == str(secret_store_path)
    assert payload["secret_key_path"] == str(secret_key_path)

    config = load_cli_config()
    profile = config.profile("work")
    assert profile is not None
    assert config.default_profile == "work"
    assert profile.app_id == "cli_work"
    assert profile.auth_mode == "auto"
    assert profile.base_url == "https://open.example.test/open-apis"
    assert profile.timeout_seconds == 45.0
    assert profile.token_store_path == str(token_store_path)
    assert profile.app_secret_ref is not None

    assert secret_key_path.exists()
    assert "work-secret-value" not in config_path.read_text(encoding="utf-8")
    assert "work-secret-value" not in secret_store_path.read_text(encoding="utf-8")
    assert resolve_secret_store().get(profile.app_secret_ref) == "work-secret-value"

    code = cli.main(["config", "show", "--profile", "work", "--format", "json"])
    assert code == 0
    show_payload = json.loads(capsys.readouterr().out)
    assert show_payload["profile"] == "work"
    assert show_payload["auth_mode"] == "auto"
    assert show_payload["base_url"] == "https://open.example.test/open-apis"
    assert show_payload["timeout_seconds"] == 45.0
    assert show_payload["token_store_path"] == str(token_store_path)
    assert show_payload["has_app_secret"] is True

    code = cli.main(["config", "list-profiles", "--format", "json"])
    assert code == 0
    list_payload = json.loads(capsys.readouterr().out)
    assert list_payload["count"] == 1
    assert list_payload["default_profile"] == "work"
    assert list_payload["profiles"][0]["profile"] == "work"
    assert list_payload["profiles"][0]["default"] is True
    assert list_payload["profiles"][0]["app_id"] == "cli_work"
    assert list_payload["profiles"][0]["auth_mode"] == "auto"
    assert list_payload["profiles"][0]["base_url"] == "https://open.example.test/open-apis"
    assert list_payload["profiles"][0]["has_app_secret"] is True


def test_config_set_default_and_remove_profile(
    monkeypatch: Any, tmp_path: Path, capsys: Any
) -> None:
    _configure_cli_paths(monkeypatch, tmp_path)

    code = cli.main(
        [
            "config",
            "init",
            "--profile",
            "work",
            "--app-id",
            "cli_work",
            "--app-secret",
            "work-secret",
            "--format",
            "json",
        ]
    )
    assert code == 0
    capsys.readouterr()

    code = cli.main(
        [
            "config",
            "init",
            "--profile",
            "staging",
            "--app-id",
            "cli_staging",
            "--app-secret",
            "staging-secret",
            "--format",
            "json",
        ]
    )
    assert code == 0
    capsys.readouterr()

    config = load_cli_config()
    staging = config.profile("staging")
    assert staging is not None
    assert staging.app_secret_ref is not None
    staging_secret_ref = staging.app_secret_ref

    code = cli.main(["config", "set-default-profile", "staging", "--format", "json"])
    assert code == 0
    default_payload = json.loads(capsys.readouterr().out)
    assert default_payload["profile"] == "staging"
    assert default_payload["default_profile"] == "staging"

    code = cli.main(["config", "show", "--format", "json"])
    assert code == 0
    show_payload = json.loads(capsys.readouterr().out)
    assert show_payload["profile"] == "staging"
    assert show_payload["default"] is True

    code = cli.main(["config", "remove-profile", "staging", "--format", "json"])
    assert code == 0
    remove_payload = json.loads(capsys.readouterr().out)
    assert remove_payload["profile"] == "staging"
    assert remove_payload["deleted"] is True
    assert remove_payload["removed_secret"] is True
    assert remove_payload["default_profile"] == "work"

    updated = load_cli_config()
    assert updated.default_profile == "work"
    assert updated.profile("staging") is None
    assert updated.profile("work") is not None
    assert resolve_secret_store().get(staging_secret_ref) is None


def test_auth_runtime_uses_profile_credentials_and_token_store_path(
    monkeypatch: Any, tmp_path: Path, capsys: Any
) -> None:
    _configure_cli_paths(monkeypatch, tmp_path)
    token_store_path = tmp_path / "tokens" / "work.json"
    monkeypatch.setattr("sys.stdin", io.StringIO("profile-secret"))

    code = cli.main(
        [
            "config",
            "init",
            "--profile",
            "work",
            "--app-id",
            "cli_profile",
            "--app-secret-stdin",
            "--auth-mode",
            "auto",
            "--base-url",
            "https://profile.example.test/open-apis",
            "--timeout",
            "12.5",
            "--token-store",
            str(token_store_path),
            "--set-default",
            "--format",
            "json",
        ]
    )
    assert code == 0
    capsys.readouterr()

    context = _resolve_user_token_store_context(_auth_args("work"))
    assert context.enabled is True
    assert context.profile == "work"
    assert context.store_path == token_store_path
    assert context.loaded_token is None

    captured: dict[str, Any] = {}

    def _fake_get_access_token(self: Any) -> str:
        captured["app_id"] = self.config.app_id
        captured["app_secret"] = self.config.app_secret
        captured["auth_mode"] = self.config.auth_mode
        captured["base_url"] = self.config.base_url
        captured["timeout_seconds"] = self.config.timeout_seconds
        return "profile-access-token"

    monkeypatch.setattr("feishu_bot_sdk.feishu.FeishuClient.get_access_token", _fake_get_access_token)

    code = cli.main(["auth", "token", "--profile", "work", "--format", "json"])
    assert code == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["auth_mode"] == "auto"
    assert payload["access_token"] == "profile-access-token"
    assert captured == {
        "app_id": "cli_profile",
        "app_secret": "profile-secret",
        "auth_mode": "auto",
        "base_url": "https://profile.example.test/open-apis",
        "timeout_seconds": 12.5,
    }


def test_config_migrate_token_store_imports_profiles(
    monkeypatch: Any, tmp_path: Path, capsys: Any
) -> None:
    _, secret_store_path, secret_key_path = _configure_cli_paths(monkeypatch, tmp_path)
    legacy_store_path = tmp_path / "legacy" / "tokens.json"
    legacy_store_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_store_path.write_text(
        json.dumps(
            {
                "version": 1,
                "profiles": {
                    "default": {
                        "access_token": "legacy-access-default",
                        "refresh_token": "legacy-refresh-default",
                    },
                    "work": {
                        "access_token": "legacy-access-work",
                        "refresh_token": "legacy-refresh-work",
                    },
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("sys.stdin", io.StringIO("migrated-secret"))

    code = cli.main(
        [
            "config",
            "migrate-token-store",
            "--from",
            str(legacy_store_path),
            "--app-id",
            "cli_migrated",
            "--app-secret-stdin",
            "--auth-mode",
            "auto",
            "--base-url",
            "https://migration.example.test/open-apis",
            "--timeout",
            "22",
            "--default-profile",
            "work",
            "--format",
            "json",
        ]
    )
    assert code == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["source_path"] == str(legacy_store_path)
    assert payload["token_store_path"] == str(legacy_store_path)
    assert payload["imported_count"] == 2
    assert payload["default_profile"] == "work"
    assert payload["missing_app_credentials_profiles"] == []
    assert payload["secret_store_path"] == str(secret_store_path)
    assert payload["secret_key_path"] == str(secret_key_path)

    config = load_cli_config()
    assert config.default_profile == "work"
    default_profile = config.profile("default")
    work_profile = config.profile("work")
    assert default_profile is not None
    assert work_profile is not None
    assert default_profile.app_id == "cli_migrated"
    assert work_profile.app_id == "cli_migrated"
    assert default_profile.auth_mode == "auto"
    assert work_profile.auth_mode == "auto"
    assert default_profile.base_url == "https://migration.example.test/open-apis"
    assert work_profile.base_url == "https://migration.example.test/open-apis"
    assert default_profile.timeout_seconds == 22.0
    assert work_profile.timeout_seconds == 22.0
    assert default_profile.token_store_path == str(legacy_store_path)
    assert work_profile.token_store_path == str(legacy_store_path)
    assert default_profile.app_secret_ref is not None
    assert work_profile.app_secret_ref is not None
    assert resolve_secret_store().get(default_profile.app_secret_ref) == "migrated-secret"
    assert resolve_secret_store().get(work_profile.app_secret_ref) == "migrated-secret"

    context = _resolve_user_token_store_context(_auth_args("work"))
    assert context.enabled is True
    assert context.profile == "work"
    assert context.store_path == legacy_store_path
    assert context.loaded_token is not None
    assert context.loaded_token.access_token == "legacy-access-work"
    assert context.loaded_token.refresh_token == "legacy-refresh-work"


def test_profile_manager_resolves_default_profile(
    monkeypatch: Any, tmp_path: Path, capsys: Any
) -> None:
    _configure_cli_paths(monkeypatch, tmp_path)
    code = cli.main(
        [
            "config",
            "init",
            "--profile",
            "default",
            "--app-id",
            "cli_default",
            "--app-secret",
            "default-secret",
            "--format",
            "json",
        ]
    )
    assert code == 0
    capsys.readouterr()

    code = cli.main(
        [
            "config",
            "init",
            "--profile",
            "work",
            "--app-id",
            "cli_work",
            "--app-secret",
            "work-secret",
            "--set-default",
            "--format",
            "json",
        ]
    )
    assert code == 0
    capsys.readouterr()

    name, profile, config = resolve_cli_profile()
    assert name == "work"
    assert profile is not None
    assert profile.name == "work"
    assert config.default_profile == "work"
    assert [item.name for item in list_cli_profiles(config=config)] == ["default", "work"]
