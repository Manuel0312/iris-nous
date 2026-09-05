"""Tests for synthetic EEG acquisition."""

from __future__ import annotations

from bci_iot.acquisition import SyntheticEEGSource


def test_synthetic_source_yields_expected_shape() -> None:
    source = SyntheticEEGSource(
        sample_rate_hz=250.0,
        n_channels=4,
        window_seconds=0.5,
        max_windows=3,
        seed=0,
    )
    with source:
        windows = list(source.iter_windows())

    assert len(windows) == 3
    assert windows[0].data.shape == (4, 125)
    assert windows[0].channel_names == ("CH1", "CH2", "CH3", "CH4")
