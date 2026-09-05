"""Digital filters for EEG cleaning."""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.signal import butter, filtfilt, iirnotch


def bandpass_filter(
    data: NDArray[np.floating[Any]],
    sample_rate_hz: float,
    low_hz: float,
    high_hz: float,
    order: int = 4,
) -> NDArray[np.floating[Any]]:
    """Apply a zero-phase Butterworth bandpass filter channel-wise.

    Args:
        data: Array shaped ``(n_channels, n_samples)``.
        sample_rate_hz: Sampling frequency in Hz.
        low_hz: High-pass cutoff.
        high_hz: Low-pass cutoff.
        order: Butterworth filter order.

    Returns:
        Filtered array with the same shape as ``data``.
    """

    if data.ndim != 2:
        raise ValueError("data must have shape (n_channels, n_samples)")
    if not 0 < low_hz < high_hz < sample_rate_hz / 2:
        raise ValueError("Invalid bandpass cutoffs for the given sample rate")

    nyquist = sample_rate_hz / 2.0
    sos_b, sos_a = butter(order, [low_hz / nyquist, high_hz / nyquist], btype="band")
    return filtfilt(sos_b, sos_a, data, axis=1)


def notch_filter(
    data: NDArray[np.floating[Any]],
    sample_rate_hz: float,
    notch_hz: float,
    quality: float = 30.0,
) -> NDArray[np.floating[Any]]:
    """Apply a zero-phase notch filter (e.g. 50 Hz mains) channel-wise."""

    if data.ndim != 2:
        raise ValueError("data must have shape (n_channels, n_samples)")
    if notch_hz <= 0 or notch_hz >= sample_rate_hz / 2:
        raise ValueError("notch_hz must be within (0, Nyquist)")

    b, a = iirnotch(notch_hz, quality, fs=sample_rate_hz)
    return filtfilt(b, a, data, axis=1)
