from __future__ import annotations

import pytest

from feishu_bot_sdk.cli.runtime.risk import (
    RiskLevel,
    assert_risk_allowed,
    risk_metadata,
)


def test_risk_metadata_normalizes_known_and_unknown_values() -> None:
    assert risk_metadata("read") == {"risk": "read", "requires_confirmation": False}
    assert risk_metadata("write") == {"risk": "write", "requires_confirmation": False}
    assert risk_metadata("high-risk-write") == {
        "risk": "high-risk-write",
        "requires_confirmation": True,
    }
    assert risk_metadata("") == {"risk": "read", "requires_confirmation": False}


def test_assert_risk_allowed_requires_yes_for_high_risk_writes() -> None:
    assert_risk_allowed(RiskLevel.WRITE, yes=False, command="drive +upload")

    with pytest.raises(ValueError, match="requires --yes"):
        assert_risk_allowed(RiskLevel.HIGH_RISK_WRITE, yes=False, command="drive +delete")

    assert_risk_allowed(RiskLevel.HIGH_RISK_WRITE, yes=True, command="drive +delete")

