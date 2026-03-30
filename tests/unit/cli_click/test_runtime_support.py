from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click
import pytest

from feishu_bot_sdk.cli.context import CLIContext
from feishu_bot_sdk.cli.groups import service as service_group
from feishu_bot_sdk.cli.runtime import output as output_runtime
from feishu_bot_sdk.cli.runtime import registry as registry_runtime
from feishu_bot_sdk.cli.runtime import scope_registry
from feishu_bot_sdk.cli.runtime.identity import resolve_identity
from feishu_bot_sdk.cli.runtime.registry import ServiceSpec
from feishu_bot_sdk.cli.shortcuts import attach_shortcuts
from feishu_bot_sdk.exceptions import HTTPRequestError


def test_load_auto_approve_scopes_uses_nested_recommend_allow_deny(
    monkeypatch: Any, tmp_path: Path
) -> None:
    (tmp_path / "scope_priorities.json").write_text(
        json.dumps(
            [
                {"scope_name": "drive:file:upload", "recommend": "true"},
                {"scope_name": "docs:doc", "recommend": "false"},
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "scope_overrides.json").write_text(
        json.dumps(
            {
                "recommend": {
                    "allow": ["docs:doc"],
                    "deny": ["drive:file:upload"],
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(scope_registry, "_scope_file", lambda name: tmp_path / name)
    scope_registry.load_auto_approve_scopes.cache_clear()
    try:
        approved = scope_registry.load_auto_approve_scopes()
    finally:
        scope_registry.load_auto_approve_scopes.cache_clear()
    assert "docs:doc" in approved
    assert "drive:file:upload" not in approved


def test_print_error_outputs_structured_json_envelope(capsys: Any) -> None:
    code = output_runtime._print_error(
        "bad input",
        exit_code=2,
        output_format="json",
        error_type="validation_error",
    )
    assert code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "ok": False,
        "error": {
            "type": "validation_error",
            "code": "invalid_input",
            "message": "bad input",
            "hint": None,
            "retryable": False,
        },
        "exit_code": 2,
    }


def test_build_http_error_detail_preserves_structured_fields() -> None:
    exc = HTTPRequestError(
        "http request failed",
        status_code=400,
        response_text=(
            '{"code":99991679,"msg":"required one of these privileges under the user identity: '
            '[contact:user:search, contact:contact.base:readonly]"}'
        ),
    )
    detail = output_runtime._build_http_error_detail(exc)
    assert detail["type"] == "http_error"
    assert detail["code"] == 99991679
    assert detail["status_code"] == 400
    assert "missing user scopes" in detail["hint"]
    assert "response_excerpt" in detail


def test_metadata_available_requires_service_json_files(
    monkeypatch: Any, tmp_path: Path
) -> None:
    services_dir = tmp_path / "metadata" / "services"
    services_dir.mkdir(parents=True)
    monkeypatch.setattr(registry_runtime, "services_root", lambda: services_dir)
    assert registry_runtime.metadata_available() is False
    (services_dir / "drive.json").write_text("{}", encoding="utf-8")
    assert registry_runtime.metadata_available() is True


def test_resolve_identity_priority_chain(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        "feishu_bot_sdk.cli.runtime.identity.available_identities",
        lambda _ctx: (True, True),
    )
    monkeypatch.setattr(
        "feishu_bot_sdk.cli.runtime.identity._resolve_default_as",
        lambda _ctx: "user",
    )
    explicit = resolve_identity(CLIContext(as_type="bot"), ("user", "bot"))
    assert explicit.identity == "bot"
    assert explicit.source == "flag"

    metadata_locked = resolve_identity(CLIContext(as_type="auto"), ("bot",))
    assert metadata_locked.identity == "bot"
    assert metadata_locked.source == "metadata"

    default_as = resolve_identity(CLIContext(as_type="auto"), ("user", "bot"))
    assert default_as.identity == "user"
    assert default_as.source == "default_as"


def test_resolve_identity_falls_back_to_login_state_and_then_supported_default(
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        "feishu_bot_sdk.cli.runtime.identity._resolve_default_as",
        lambda _ctx: "",
    )
    monkeypatch.setattr(
        "feishu_bot_sdk.cli.runtime.identity.available_identities",
        lambda _ctx: (True, False),
    )
    login_state = resolve_identity(CLIContext(as_type="auto"), ("user", "bot"))
    assert login_state.identity == "user"
    assert login_state.source == "login_state"

    monkeypatch.setattr(
        "feishu_bot_sdk.cli.runtime.identity.available_identities",
        lambda _ctx: (False, False),
    )
    fallback = resolve_identity(CLIContext(as_type="auto"), ("bot", "user"))
    assert fallback.identity == "bot"
    assert fallback.source == "fallback"


def test_register_service_groups_merges_existing_shortcut_group(monkeypatch: Any) -> None:
    service = ServiceSpec(
        name="bitable",
        service_path="/open-apis/bitable/v1/apps",
        title="Bitable",
        description="Bitable APIs",
        version="v1",
        raw={
            "resources": {
                "app": {
                    "methods": {
                        "list": {
                            "httpMethod": "GET",
                            "path": "",
                            "accessTokens": ["tenant"],
                        }
                    }
                }
            }
        },
    )
    root = click.Group()
    bitable = click.Group("bitable", help="bitable shortcuts")
    attach_shortcuts(bitable, "bitable")
    root.add_command(bitable)
    monkeypatch.setattr(service_group, "list_services", lambda: (service,))

    service_group.register_service_groups(root)

    merged = root.commands["bitable"]
    assert isinstance(merged, click.Group)
    assert "+create-from-csv" in merged.commands
    assert "app" in merged.commands
    app_group = merged.commands["app"]
    assert isinstance(app_group, click.Group)
    assert "list" in app_group.commands


def test_sleep_between_pages_sleeps_in_small_chunks(monkeypatch: Any) -> None:
    calls: list[float] = []

    def _fake_sleep(seconds: float) -> None:
        calls.append(seconds)

    monkeypatch.setattr(service_group.time, "sleep", _fake_sleep)
    service_group._sleep_between_pages(350)
    assert calls == pytest.approx([0.1, 0.1, 0.1, 0.05], rel=0, abs=1e-9)
