"""Tests for preprocessing filters and band-power features."""

from __future__ import annotations

import numpy as np

from bci_iot.preprocessing import BandPowerExtractor, bandpass_filter
from bci_iot.types import EEGWindow


def test_bandpass_filter_preserves_shape() -> None:
    rng = np.random.default_rng(1)
    data = rng.normal(size=(2, 500))
    filtered = bandpass_filter(data, sample_rate_hz=250.0, low_hz=1.0, high_hz=40.0)
    assert filtered.shape == data.shape


def test_band_power_extractor_returns_three_features() -> None:
    rng = np.random.default_rng(2)
    window = EEGWindow(
        data=rng.normal(size=(4, 250)).astype(np.float64),
        sample_rate_hz=250.0,
        timestamp_s=0.0,
        channel_names=("CH1", "CH2", "CH3", "CH4"),
    )
    features = BandPowerExtractor(notch_hz=None).transform(window)
    assert features.values.shape == (3,)
    assert features.names == ("alpha_logpower", "beta_logpower", "alpha_beta_ratio")
