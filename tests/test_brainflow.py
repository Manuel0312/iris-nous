"""Tests for acquisition factory and BrainFlow SyntheticBoard source."""

from __future__ import annotations

import pytest

from bci_iot.acquisition import (
    SyntheticEEGSource,
    brainflow_available,
    create_eeg_source,
)
from bci_iot.config import AcquisitionSettings


def test_create_numpy_synthetic_source() -> None:
    source = create_eeg_source(
        AcquisitionSettings(source="synthetic", n_channels=4, window_seconds=0.5),
        max_windows=2,
    )
    assert isinstance(source, SyntheticEEGSource)
    with source:
        windows = list(source.iter_windows())
    assert len(windows) == 2
    assert windows[0].data.shape[0] == 4


def test_create_unknown_source_raises() -> None:
    with pytest.raises(ValueError, match="Unknown acquisition.source"):
        create_eeg_source(AcquisitionSettings(source="nope"))


@pytest.mark.skipif(not brainflow_available(), reason="brainflow not installed")
def test_brainflow_synthetic_yields_windows() -> None:
    from bci_iot.acquisition import BrainFlowSyntheticSource

    source = BrainFlowSyntheticSource(window_seconds=0.5, n_channels=4, max_windows=2)
    with source:
        windows = list(source.iter_windows())
    assert len(windows) == 2
    assert windows[0].data.shape[0] == 4
    assert windows[0].data.shape[1] == source.n_samples
    assert windows[0].sample_rate_hz > 0


@pytest.mark.skipif(not brainflow_available(), reason="brainflow not installed")
def test_factory_brainflow_synthetic() -> None:
    source = create_eeg_source(
        AcquisitionSettings(source="brainflow_synthetic", n_channels=4, window_seconds=0.5),
        max_windows=1,
    )
    with source:
        windows = list(source.iter_windows())
    assert len(windows) == 1


@pytest.mark.skipif(not brainflow_available(), reason="brainflow not installed")
def test_factory_brainflow_cyton_falls_back_without_port() -> None:
    """Senza COM port la factory non deve rompersi: SyntheticBoard."""
    from bci_iot.acquisition.brainflow_source import BrainFlowSyntheticSource

    source = create_eeg_source(
        AcquisitionSettings(source="brainflow_cyton", n_channels=4, window_seconds=0.5),
        max_windows=1,
    )
    assert isinstance(source, BrainFlowSyntheticSource)
    with source:
        windows = list(source.iter_windows())
    assert len(windows) == 1


def test_capture_one_openbci_fallback() -> None:
    from bci_iot.acquisition.brainflow_openbci import capture_one_openbci_window
    from bci_iot.acquisition.brainflow_source import brainflow_available as bf_ok

    if not bf_ok():
        pytest.skip("brainflow not installed")
    window, path = capture_one_openbci_window(
        board="synthetic",
        window_seconds=0.4,
        n_channels=4,
        fallback_synthetic=True,
    )
    assert window.data.shape[0] == 4
    assert path.startswith("brainflow_")


@pytest.mark.skipif(not brainflow_available(), reason="brainflow not installed")
def test_pipeline_end_to_end_brainflow_synthetic(tmp_path) -> None:
    """Same API path a real BrainFlow board would use: stream → features → intent → action."""
    from bci_iot.config import AppConfig, AcquisitionSettings, IntegrationsSettings, MLSettings
    from bci_iot.pipeline.factory import build_pipeline
    from bci_iot.types import ActionContext

    config = AppConfig(
        acquisition=AcquisitionSettings(
            source="brainflow_synthetic",
            n_channels=4,
            window_seconds=0.5,
        ),
        ml=MLSettings(model_path="models/baseline.joblib", confidence_threshold=0.55),
        integrations=IntegrationsSettings(dry_run=True),
    )
    runner = build_pipeline(config, max_windows_cap=5, model_path="models/baseline.joblib")
    runner.router.set_context(ActionContext.MUSIC_MODE)
    results = runner.run(max_windows=5)
    assert len(results) == 5
    assert all(r.is_clean for r in results)
    assert all(r.intent.confidence >= 0.0 for r in results)
    # With debounce, at least one routed action is expected on a stable stream.
    assert sum(1 for r in results if r.action is not None) >= 1
