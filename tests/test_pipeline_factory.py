"""Tests for pipeline factory and user calibration."""

from __future__ import annotations

from pathlib import Path

from bci_iot.accounts import ProfileStore
from bci_iot.config import AppConfig
from bci_iot.ml import calibrate_user_model
from bci_iot.pipeline import build_pipeline
from bci_iot.types import ActionContext


def test_build_pipeline_runs(tmp_path: Path) -> None:
    config = AppConfig()
    config.accounts.data_dir = str(tmp_path / "profiles")
    runner = build_pipeline(config, max_windows_cap=4, prefer_sklearn=False)
    runner.router.set_context(ActionContext.MUSIC_MODE)
    results = runner.run(max_windows=4)
    assert len(results) == 4


def test_build_pipeline_with_profile_action_map(tmp_path: Path) -> None:
    profiles = tmp_path / "profiles"
    store = ProfileStore(profiles)
    store.create_account(
        "demo",
        "secret12",
        action_map={"FOCUS": "spotify.pause"},
    )
    config = AppConfig()
    config.accounts.data_dir = str(profiles)
    runner = build_pipeline(config, username="demo", max_windows_cap=3, prefer_sklearn=False)
    assert runner.router.action_map["FOCUS"] == "spotify.pause"


def test_calibrate_user_model(tmp_path: Path) -> None:
    path, accuracy = calibrate_user_model(
        "Maria",
        models_dir=tmp_path / "models",
        n_samples=90,
        seed=3,
    )
    assert path.exists()
    assert accuracy > 0.7
    assert path.name == "maria.joblib"
