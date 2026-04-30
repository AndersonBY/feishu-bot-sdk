from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


class ContentSafetyViolation(ValueError):
    pass


@dataclass(frozen=True)
class ContentSafetyResult:
    allowed: bool
    reason: str = ""


class NoopContentSafetyScanner:
    def scan_text(
        self,
        text: str,
        *,
        context: Mapping[str, object] | None = None,
    ) -> ContentSafetyResult:
        return ContentSafetyResult(allowed=True)

    def assert_text_allowed(
        self,
        text: str,
        *,
        context: Mapping[str, object] | None = None,
    ) -> None:
        result = self.scan_text(text, context=context)
        if not result.allowed:
            raise ContentSafetyViolation(result.reason)


class BlockListContentSafetyScanner(NoopContentSafetyScanner):
    def __init__(self, blocked_terms: Sequence[str]) -> None:
        self._blocked_terms = tuple(term for term in blocked_terms if term)

    def scan_text(
        self,
        text: str,
        *,
        context: Mapping[str, object] | None = None,
    ) -> ContentSafetyResult:
        for term in self._blocked_terms:
            if term in text:
                return ContentSafetyResult(
                    allowed=False,
                    reason=f"content matched blocked term: {term}",
                )
        return ContentSafetyResult(allowed=True)


__all__ = [name for name in globals() if not name.startswith("__")]

