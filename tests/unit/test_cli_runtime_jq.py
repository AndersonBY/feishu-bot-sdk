from __future__ import annotations

import pytest

from feishu_bot_sdk.cli.runtime.jq import apply_jq_filter


def test_apply_jq_filter_supports_identity_and_dotted_paths() -> None:
    payload = {"data": {"items": [{"name": "first"}]}, "ok": True}

    assert apply_jq_filter(payload, None) == payload
    assert apply_jq_filter(payload, ".") == payload
    assert apply_jq_filter(payload, ".data.items") == [{"name": "first"}]
    assert apply_jq_filter(payload, ".data.items.0.name") == "first"


def test_apply_jq_filter_reports_unsupported_expressions() -> None:
    with pytest.raises(ValueError, match="unsupported jq expression"):
        apply_jq_filter({"items": []}, ".items[] | .name")

