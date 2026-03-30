from __future__ import annotations

import contextlib
from typing import Any

import click
import httpx

from ..context import build_cli_context, with_runtime_options
from ..runtime import _build_client, _resolve_user_token_store_context, load_cli_config
from ..runtime.identity import available_identities
from ..runtime.registry import metadata_available


@click.command("doctor", help="Run CLI health checks: config, auth, metadata, connectivity")
@click.option("--offline", is_flag=True, help="Skip network checks")
@with_runtime_options(include_identity=False)
def doctor_command(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    offline = bool(params.pop("offline", False))
    checks: list[dict[str, Any]] = []

    config = load_cli_config()
    if config.profiles:
        checks.append(_pass("config", f"{len(config.profiles)} profile(s) configured"))
    else:
        checks.append(_fail("config", "no CLI profiles configured", "run `feishu config init`"))

    checks.append(_pass("metadata", "metadata snapshot available") if metadata_available() else _fail("metadata", "metadata snapshot missing", "run sync_feishu_cli_metadata.py"))

    user_available, bot_available = available_identities(cli_ctx)
    checks.append(_pass("identity.user", "user identity is available") if user_available else _fail("identity.user", "user identity is unavailable", "run `feishu auth login`"))
    checks.append(_pass("identity.bot", "bot identity is available") if bot_available else _fail("identity.bot", "bot identity is unavailable", "configure app_id/app_secret"))

    token_context = _resolve_user_token_store_context(cli_ctx.build_args(group="doctor", auth_mode="user"))
    checks.append(_pass("token_store", str(token_context.store_path)) if token_context.enabled else _fail("token_store", "token store disabled", "omit --no-store"))

    if not offline:
        checks.extend(_network_checks(cli_ctx))
        with contextlib.suppress(Exception):
            client = _build_client(cli_ctx.build_args(group="doctor", auth_mode="user"))
            user = client.get_user_info().to_dict()
            checks.append(_pass("user_verify", user.get("open_id") or "user token verified"))

    cli_ctx.emit(
        {
            "ok": all(item["status"] != "fail" for item in checks),
            "checks": checks,
        }
    )


def _network_checks(cli_ctx: Any) -> list[dict[str, Any]]:
    targets = [
        ("open_api", (cli_ctx.base_url or "https://open.feishu.cn/open-apis").split("/open-apis")[0]),
        ("accounts", "https://accounts.feishu.cn"),
    ]
    checks: list[dict[str, Any]] = []
    for name, url in targets:
        try:
            response = httpx.head(url, timeout=10.0, follow_redirects=True)
        except Exception as exc:
            checks.append(_fail(name, f"{url} unreachable: {exc}", "check network / proxy"))
            continue
        if response.status_code >= 400:
            checks.append(_fail(name, f"{url} returned HTTP {response.status_code}", "check network / proxy"))
            continue
        checks.append(_pass(name, f"{url} reachable"))
    return checks


def _pass(name: str, message: str) -> dict[str, Any]:
    return {"name": name, "status": "pass", "message": message}


def _fail(name: str, message: str, hint: str) -> dict[str, Any]:
    return {"name": name, "status": "fail", "message": message, "hint": hint}


__all__ = ["doctor_command"]
