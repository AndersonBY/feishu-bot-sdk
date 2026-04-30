from __future__ import annotations

from importlib import metadata
from typing import Any

import click

from ..context import build_cli_context, with_runtime_options


_PACKAGE_NAME = "feishu-bot-sdk"
_PROJECT_URL = "https://github.com/AndersonBY/feishu-bot-sdk"


@click.command("update", help="Check update information for the Python package")
@click.option("--check", is_flag=True, help="Only check update status")
@click.option("--force", is_flag=True, help="Show reinstall instructions even when current")
@with_runtime_options(include_identity=False)
def update_command(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    current = _current_version()
    latest = current
    force = bool(params.get("force"))
    action = "manual_required" if force else "already_up_to_date"
    message = (
        f"{_PACKAGE_NAME} {current} is installed. Automatic self-update is disabled for "
        "the Python distribution."
    )
    hint = f"Update with your package manager, for example: pip install -U {_PACKAGE_NAME}"
    cli_ctx.emit(
        {
            "ok": True,
            "package": _PACKAGE_NAME,
            "current_version": current,
            "previous_version": current,
            "latest_version": latest,
            "action": action,
            "auto_update": False,
            "check_only": bool(params.get("check")),
            "message": message,
            "hint": hint,
            "url": _PROJECT_URL,
            "changelog": f"{_PROJECT_URL}/releases",
            "install_method": _detect_install_method(),
        },
        cli_args=cli_ctx.build_args(group="update"),
    )


def _current_version() -> str:
    try:
        return metadata.version(_PACKAGE_NAME)
    except metadata.PackageNotFoundError:
        return "0.0.0"


def _detect_install_method() -> dict[str, Any]:
    return {
        "method": "python-package",
        "auto_update_supported": False,
        "manager": "pip",
    }


__all__ = ["update_command"]
