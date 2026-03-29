from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import pytest

import feishu_bot_sdk.cli as cli


_ENV_PATH = Path(__file__).resolve().parents[4] / ".env"


def _load_env() -> dict[str, str]:
    values: dict[str, str] = {}
    if not _ENV_PATH.exists():
        return values
    for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key:
            values[key] = value
    return values


def _run_cli(argv: list[str], *, stdin_text: str | None = None) -> tuple[int, dict[str, object]]:
    stdout = io.StringIO()
    stdin = io.StringIO(stdin_text or "")
    with patch("sys.stdin", stdin), redirect_stdout(stdout):
        code = cli.main(argv)
    output = stdout.getvalue().strip()
    payload = json.loads(output) if output else {}
    return code, payload if isinstance(payload, dict) else {}


def test_cli_profile_bootstrap_and_auth_token_live(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env = _load_env()
    app_id = (env.get("APP_ID") or env.get("FEISHU_APP_ID") or "").strip()
    app_secret = (env.get("APP_SECRET") or env.get("FEISHU_APP_SECRET") or "").strip()
    if not app_id or not app_secret:
        pytest.skip("APP_ID / APP_SECRET not found in root .env")

    config_path = tmp_path / "cli-config.json"
    secret_store_path = tmp_path / "cli-secrets.json"
    secret_key_path = tmp_path / "cli-secrets.key"

    managed_env = {
        "APP_ID": "",
        "APP_SECRET": "",
        "FEISHU_APP_ID": "",
        "FEISHU_APP_SECRET": "",
        "FEISHU_AUTH_MODE": "",
        "FEISHU_USER_ACCESS_TOKEN": "",
        "FEISHU_USER_REFRESH_TOKEN": "",
        "FEISHU_CLI_CONFIG_PATH": str(config_path),
        "FEISHU_SECRET_STORE_PATH": str(secret_store_path),
        "FEISHU_SECRET_STORE_KEY_PATH": str(secret_key_path),
    }
    with patch.dict("os.environ", managed_env, clear=False):
        code, init_payload = _run_cli(
            [
                "config",
                "init",
                "--profile",
                "live",
                "--app-id",
                app_id,
                "--app-secret-stdin",
                "--set-default",
                "--format",
                "json",
            ],
            stdin_text=app_secret,
        )
        assert code == 0
        assert init_payload["profile"] == "live"
        assert init_payload["has_app_secret"] is True

        code, show_payload = _run_cli(["config", "show", "--profile", "live", "--format", "json"])
        assert code == 0
        assert show_payload["profile"] == "live"
        assert show_payload["app_id"] == app_id
        assert show_payload["has_app_secret"] is True

        code, token_payload = _run_cli(["auth", "token", "--profile", "live", "--format", "json"])
        assert code == 0
        access_token = str(token_payload.get("access_token") or "").strip()
        assert access_token
