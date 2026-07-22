"""Tests for configuration loading."""

from __future__ import annotations

from pathlib import Path

from bci_iot.config import load_app_config


def test_load_default_config() -> None:
    root = Path(__file__).resolve().parents[1]
    config = load_app_config(root / "configs" / "default.yaml")
    assert config.acquisition.source == "synthetic"
    assert config.acquisition.sample_rate_hz == 250.0
    assert config.integrations.dry_run is True
    assert config.accounts.require_login is True
