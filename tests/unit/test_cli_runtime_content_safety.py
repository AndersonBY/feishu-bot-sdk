from __future__ import annotations

import pytest

from feishu_bot_sdk.cli.runtime.content_safety import (
    BlockListContentSafetyScanner,
    ContentSafetyViolation,
    NoopContentSafetyScanner,
)


def test_noop_content_safety_scanner_allows_any_payload() -> None:
    scanner = NoopContentSafetyScanner()

    result = scanner.scan_text("anything", context={"command": "mail +send"})

    assert result.allowed is True
    assert result.reason == ""


def test_block_list_content_safety_scanner_blocks_matching_text() -> None:
    scanner = BlockListContentSafetyScanner(["secret-token"])

    with pytest.raises(ContentSafetyViolation, match="secret-token"):
        scanner.assert_text_allowed("contains secret-token")

