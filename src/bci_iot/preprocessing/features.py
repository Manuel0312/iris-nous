"""Band-power feature extraction (Alpha / Beta) via Welch PSD."""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.signal import welch

from bci_iot.preprocessing.artifacts import ArtifactDetector, ArtifactReport
from bci_iot.preprocessing.filters import bandpass_filter, notch_filter
from bci_iot.types import EEGWindow, FeatureVector


def _band_power(
    freqs: NDArray[np.floating[Any]],
    psd: NDArray[np.floating[Any]],
    band: tuple[float, float],
) -> float:
    low, high = band
    mask = (freqs >= low) & (freqs < high)
    if not np.any(mask):
        return 0.0
    return float(np.trapezoid(psd[mask], freqs[mask]))


class BandPowerExtractor:
    """Filter, optionally clean artifacts, then extract mean Alpha/Beta features."""

    def __init__(
        self,
        *,
        bandpass_hz: tuple[float, float] = (1.0, 40.0),
        notch_hz: float | None = 50.0,
        alpha_band_hz: tuple[float, float] = (8.0, 12.0),
        beta_band_hz: tuple[float, float] = (13.0, 30.0),
        artifact_detector: ArtifactDetector | None = None,
        reject_dirty_windows: bool = True,
    ) -> None:
        self.bandpass_hz = bandpass_hz
        self.notch_hz = notch_hz
        self.alpha_band_hz = alpha_band_hz
        self.beta_band_hz = beta_band_hz
        self.artifact_detector = artifact_detector if artifact_detector is not None else ArtifactDetector()
        self.reject_dirty_windows = reject_dirty_windows
        self.feature_names = ("alpha_logpower", "beta_logpower", "alpha_beta_ratio")
        self.last_artifact_report: ArtifactReport | None = None

    def transform(self, window: EEGWindow) -> FeatureVector:
        """Filter ``window`` and return a compact spectral feature vector."""

        cleaned, report = self.artifact_detector.clean(window)
        self.last_artifact_report = report

        data = bandpass_filter(
            cleaned.data,
            cleaned.sample_rate_hz,
            self.bandpass_hz[0],
            self.bandpass_hz[1],
        )
        if self.notch_hz is not None and self.notch_hz < cleaned.sample_rate_hz / 2:
            data = notch_filter(data, cleaned.sample_rate_hz, self.notch_hz)

        usable = [
            channel
            for idx, channel in enumerate(data)
            if idx not in report.rejected_channels
        ]
        if not usable:
            values = np.zeros(3, dtype=np.float64)
            return FeatureVector(
                values=values,
                names=self.feature_names,
                timestamp_s=window.timestamp_s,
                is_clean=False,
                artifact_flags=report.flags,
            )

        alpha_powers: list[float] = []
        beta_powers: list[float] = []
        for channel in usable:
            freqs, psd = welch(channel, fs=cleaned.sample_rate_hz, nperseg=min(256, channel.size))
            alpha_powers.append(_band_power(freqs, psd, self.alpha_band_hz))
            beta_powers.append(_band_power(freqs, psd, self.beta_band_hz))

        alpha = float(np.mean(alpha_powers))
        beta = float(np.mean(beta_powers))
        eps = 1e-12
        values = np.array(
            [
                np.log10(alpha + eps),
                np.log10(beta + eps),
                alpha / (beta + eps),
            ],
            dtype=np.float64,
        )
        is_clean = True if not self.reject_dirty_windows else report.is_clean
        return FeatureVector(
            values=values,
            names=self.feature_names,
            timestamp_s=window.timestamp_s,
            is_clean=is_clean,
            artifact_flags=report.flags,
        )
