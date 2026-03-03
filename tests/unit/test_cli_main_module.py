from __future__ import annotations

import runpy

import pytest

import feishu_bot_sdk.cli as cli


def test_python_m_cli_invokes_cli_main(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def _fake_main(argv: object = None) -> int:
        captured["argv"] = argv
        return 37

    monkeypatch.setattr(cli, "main", _fake_main)

    with pytest.raises(SystemExit) as exc:
        runpy.run_module("feishu_bot_sdk.cli", run_name="__main__")

    assert exc.value.code == 37
    assert captured["argv"] is None
