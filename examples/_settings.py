import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict


@dataclass(frozen=True)
class FeishuAppSettings:
    app_id: str
    app_secret: str
    encrypt_key: str | None = None
    verification_token: str | None = None


def load_settings() -> FeishuAppSettings:
    values = _load_env_values()
    app_id = values.get("APP_ID") or values.get("FEISHU_APP_ID")
    app_secret = values.get("APP_SECRET") or values.get("FEISHU_APP_SECRET")
    encrypt_key = values.get("ENCRYPT_KEY") or values.get("FEISHU_ENCRYPT_KEY")
    verification_token = values.get("VERIFICATION_TOKEN") or values.get("FEISHU_VERIFICATION_TOKEN")
    if not app_id or not app_secret:
        raise RuntimeError("missing APP_ID/APP_SECRET in environment or .env")
    return FeishuAppSettings(
        app_id=app_id,
        app_secret=app_secret,
        encrypt_key=encrypt_key,
        verification_token=verification_token,
    )


def _load_env_values() -> Dict[str, str]:
    values: Dict[str, str] = {}
    for key, value in os.environ.items():
        values[key] = value

    for candidate in _candidate_env_files():
        if not candidate.exists():
            continue
        for line in candidate.read_text(encoding="utf-8").splitlines():
            parsed = _parse_line(line)
            if parsed is None:
                continue
            key, value = parsed
            values.setdefault(key, value)
        break
    return values


def _candidate_env_files() -> list[Path]:
    cwd = Path.cwd()
    script_dir = Path(__file__).resolve().parent
    return [
        cwd / ".env",
        cwd.parent / ".env",
        script_dir.parent / ".env",
        script_dir.parent.parent / ".env",
    ]


def _parse_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if "=" not in stripped:
        return None
    key, value = stripped.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        return None
    return key, value
