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
