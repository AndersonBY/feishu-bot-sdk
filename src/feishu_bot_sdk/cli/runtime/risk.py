from __future__ import annotations

from enum import Enum


class RiskLevel(str, Enum):
    READ = "read"
    WRITE = "write"
    HIGH_RISK_WRITE = "high-risk-write"


def normalize_risk(value: str | RiskLevel | None) -> RiskLevel:
    if isinstance(value, RiskLevel):
        return value
    normalized = str(value or "").strip().lower()
    if normalized == RiskLevel.WRITE:
        return RiskLevel.WRITE
    if normalized == RiskLevel.HIGH_RISK_WRITE:
        return RiskLevel.HIGH_RISK_WRITE
    return RiskLevel.READ


def risk_metadata(value: str | RiskLevel | None) -> dict[str, object]:
    risk = normalize_risk(value)
    return {
        "risk": risk.value,
        "requires_confirmation": risk is RiskLevel.HIGH_RISK_WRITE,
    }


def assert_risk_allowed(value: str | RiskLevel | None, *, yes: bool, command: str) -> None:
    risk = normalize_risk(value)
    if risk is RiskLevel.HIGH_RISK_WRITE and not yes:
        raise ValueError(f"{command} is high-risk-write and requires --yes")


__all__ = [name for name in globals() if not name.startswith("__")]
