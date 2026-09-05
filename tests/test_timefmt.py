"""Tests for Italian access-time formatting."""

from __future__ import annotations

from bci_iot.accounts.timefmt import format_access_it


def test_format_access_it_rome() -> None:
    # 22:30 UTC in July → 00:30 next day in Italy (CEST)
    text = format_access_it("2026-07-20T22:30:00+00:00")
    assert "alle ore" in text
    assert "/" in text
    assert format_access_it("") == "—"
    assert format_access_it(None) == "—"
