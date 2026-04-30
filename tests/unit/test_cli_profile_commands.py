from __future__ import annotations

import json
import io
from pathlib import Path
from typing import Any

import feishu_bot_sdk.cli as cli
from feishu_bot_sdk.cli.runtime import load_cli_config, resolve_secret_store


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
    monkeypatch.setenv("FEISHU_SECRET_STORE_BACKEND", "encrypted_file")
    for key in _CLEARED_ENV_KEYS:
        if key != "FEISHU_SECRET_STORE_BACKEND":
            monkeypatch.delenv(key, raising=False)
    return config_path, secret_store_path, secret_key_path


def test_profile_add_list_use_rename_and_remove(
    monkeypatch: Any,
    tmp_path: Path,
    capsys: Any,
) -> None:
    _configure_cli_paths(monkeypatch, tmp_path)
    monkeypatch.setattr("sys.stdin", io.StringIO("profile-secret"))

    code = cli.main(
        [
            "profile",
            "add",
            "--name",
            "work",
            "--app-id",
            "cli_work",
            "--app-secret-stdin",
            "--brand",
            "feishu",
            "--lang",
            "zh",
            "--use",
            "--format",
            "json",
        ]
    )
    assert code == 0
    add_payload = json.loads(capsys.readouterr().out)
    assert add_payload["name"] == "work"
    assert add_payload["appId"] == "cli_work"
    assert add_payload["brand"] == "feishu"
    assert add_payload["active"] is True
    assert add_payload["has_app_secret"] is True

    config = load_cli_config()
    work = config.profile("work")
    assert config.default_profile == "work"
    assert work is not None
    assert work.app_id == "cli_work"
    assert work.brand == "feishu"
    assert work.lang == "zh"
    assert work.app_secret_ref is not None
    assert resolve_secret_store().get(work.app_secret_ref) == "profile-secret"

    code = cli.main(
        [
            "profile",
            "add",
            "--name",
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

    code = cli.main(["profile", "list", "--format", "json"])
    assert code == 0
    list_payload = json.loads(capsys.readouterr().out)
    assert [item["name"] for item in list_payload] == ["staging", "work"]
    assert [item["active"] for item in list_payload] == [False, True]
    assert list_payload[1]["appId"] == "cli_work"

    code = cli.main(["profile", "use", "staging", "--format", "json"])
    assert code == 0
    use_payload = json.loads(capsys.readouterr().out)
    assert use_payload["name"] == "staging"
    assert use_payload["active"] is True
    assert use_payload["previous_profile"] == "work"
    assert load_cli_config().default_profile == "staging"

    code = cli.main(["profile", "rename", "staging", "prod", "--format", "json"])
    assert code == 0
    rename_payload = json.loads(capsys.readouterr().out)
    assert rename_payload["old_name"] == "staging"
    assert rename_payload["name"] == "prod"
    assert rename_payload["active"] is True

    renamed = load_cli_config()
    assert renamed.profile("staging") is None
    prod = renamed.profile("prod")
    assert prod is not None
    assert prod.app_id == "cli_staging"
    assert renamed.default_profile == "prod"

    code = cli.main(["profile", "remove", "prod", "--format", "json"])
    assert code == 0
    remove_payload = json.loads(capsys.readouterr().out)
    assert remove_payload["name"] == "prod"
    assert remove_payload["deleted"] is True
    assert remove_payload["default_profile"] == "work"

    updated = load_cli_config()
    assert updated.profile("prod") is None
    assert updated.profile("work") is not None
    assert updated.default_profile == "work"
