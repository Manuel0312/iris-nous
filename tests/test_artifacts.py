"""Tests for artifact detection and cleaning."""

from __future__ import annotations

import numpy as np

from bci_iot.preprocessing import ArtifactDetector
from bci_iot.types import EEGWindow


def _window(data: np.ndarray, sample_rate_hz: float = 250.0) -> EEGWindow:
    return EEGWindow(
        data=data.astype(np.float64),
        sample_rate_hz=sample_rate_hz,
        timestamp_s=0.0,
        channel_names=tuple(f"CH{i+1}" for i in range(data.shape[0])),
    )


def test_detects_high_amplitude_channel() -> None:
    clean = np.random.default_rng(0).normal(0, 5, size=(4, 250))
    dirty = clean.copy()
    dirty[1, 100] = 500.0
    report = ArtifactDetector(peak_to_peak_uv=100.0).analyze(_window(dirty))
    assert 1 in report.rejected_channels
    assert any("high_amplitude" in flag for flag in report.flags)


def test_clean_zeros_rejected_channels() -> None:
    t = np.linspace(0.0, 1.0, 250, endpoint=False)
    data = np.vstack([5.0 * np.sin(2 * np.pi * 10.0 * t) for _ in range(4)])
    data[2, :] = 400.0  # flat extreme offset → reject this channel only
    detector = ArtifactDetector(peak_to_peak_uv=100.0, hf_ratio_threshold=0.9)
    cleaned, report = detector.clean(_window(data))
    assert report.rejected_channels == (2,)
    assert np.allclose(cleaned.data[2], 0.0)
    assert report.is_clean is True


def test_too_many_bad_channels_marks_window_dirty() -> None:
    data = np.full((4, 250), 400.0, dtype=np.float64)
    report = ArtifactDetector(peak_to_peak_uv=100.0, max_rejected_fraction=0.5).analyze(
        _window(data)
    )
    assert report.is_clean is False
    assert "window:too_many_bad_channels" in report.flags
