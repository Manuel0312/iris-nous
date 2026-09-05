"""Tests for thesis experiment runner (offline surrogate)."""

from __future__ import annotations

from pathlib import Path

from bci_iot.experiments import run_surrogate_experiment
from bci_iot.experiments.moabb_loader import moabb_status
from bci_iot.experiments.surrogate import build_surrogate_bundle


def test_build_surrogate_bundle_shapes() -> None:
    bundle = build_surrogate_bundle(n_subjects=3, windows_per_class=4, seed=1)
    assert bundle.features.shape[0] == 3 * 4 * 4
    assert bundle.features.shape[1] == 3
    assert set(bundle.labels) == {"FOCUS", "ACCEPT", "REJECT", "RELAX"}
    assert len(set(bundle.subjects.tolist())) == 3


def test_run_surrogate_writes_reports(tmp_path: Path) -> None:
    out = tmp_path / "exp"
    report = run_surrogate_experiment(
        n_subjects=4,
        windows_per_class=5,
        seed=7,
        out_dir=out,
    )
    assert report.mode == "surrogate"
    assert 0.0 <= report.loso["mean_accuracy"] <= 1.0
    assert 0.0 <= report.kfold["mean_accuracy"] <= 1.0
    assert (out / "latest.json").exists()
    assert (out / "latest.md").exists()
    assert "Leave-one-subject-out" in (out / "latest.md").read_text(encoding="utf-8")


def test_moabb_status_is_structured() -> None:
    status = moabb_status()
    assert isinstance(status.available, bool)
    assert status.detail
