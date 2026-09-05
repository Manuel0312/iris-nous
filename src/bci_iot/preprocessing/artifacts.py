"""Heuristic EEG artifact detection (amplitude, flatline, high-frequency energy).

This is a software-first stand-in for EOG/EMG cleaning. Channels flagged as bad
are zeroed before feature extraction so extreme transients do not dominate α/β
estimates. Replace/extend with ICA once real headset data is available.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from bci_iot.types import EEGWindow


@dataclass(frozen=True, slots=True)
class ArtifactReport:
    """Per-window artifact summary used by preprocessing and the pipeline."""

    is_clean: bool
    rejected_channels: tuple[int, ...]
    flags: tuple[str, ...]


class ArtifactDetector:
    """Detect channels corrupted by blink-like spikes, flatlines, or EMG bursts."""

    def __init__(
        self,
        *,
        peak_to_peak_uv: float = 500.0,
        flatline_std_uv: float = 0.5,
        hf_ratio_threshold: float = 0.55,
        hf_cutoff_hz: float = 40.0,
        max_rejected_fraction: float = 0.5,
    ) -> None:
        if peak_to_peak_uv <= 0 or flatline_std_uv < 0:
            raise ValueError("Invalid amplitude thresholds")
        if not 0.0 < max_rejected_fraction <= 1.0:
            raise ValueError("max_rejected_fraction must be in (0, 1]")
        self.peak_to_peak_uv = peak_to_peak_uv
        self.flatline_std_uv = flatline_std_uv
        self.hf_ratio_threshold = hf_ratio_threshold
        self.hf_cutoff_hz = hf_cutoff_hz
        self.max_rejected_fraction = max_rejected_fraction

    def analyze(self, window: EEGWindow) -> ArtifactReport:
        """Return which channels look artifactual in ``window``."""

        rejected: list[int] = []
        flags: list[str] = []
        data = window.data
        n_channels = data.shape[0]

        for idx, channel in enumerate(data):
            channel_flags = self._channel_flags(channel, window.sample_rate_hz)
            if channel_flags:
                rejected.append(idx)
                flags.extend(f"ch{idx}:{flag}" for flag in channel_flags)

        rejected_t = tuple(rejected)
        too_many = (len(rejected_t) / max(n_channels, 1)) > self.max_rejected_fraction
        if too_many:
            flags.append("window:too_many_bad_channels")
        elif rejected_t:
            # Minority bad channels: still usable after zeroing them.
            flags.append("window:partial_channel_rejection")

        return ArtifactReport(
            is_clean=not too_many,
            rejected_channels=rejected_t,
            flags=tuple(dict.fromkeys(flags)),
        )

    def clean(self, window: EEGWindow) -> tuple[EEGWindow, ArtifactReport]:
        """Zero rejected channels and return a cleaned copy plus the report."""

        report = self.analyze(window)
        if not report.rejected_channels:
            return window, report

        cleaned = np.array(window.data, dtype=np.float64, copy=True)
        cleaned[list(report.rejected_channels), :] = 0.0
        cleaned_window = EEGWindow(
            data=cleaned,
            sample_rate_hz=window.sample_rate_hz,
            timestamp_s=window.timestamp_s,
            channel_names=window.channel_names,
        )
        return cleaned_window, report

    def _channel_flags(
        self,
        channel: NDArray[np.floating[Any]],
        sample_rate_hz: float,
    ) -> list[str]:
        flags: list[str] = []
        peak_to_peak = float(np.ptp(channel))
        if peak_to_peak > self.peak_to_peak_uv:
            flags.append("high_amplitude")

        std = float(np.std(channel))
        if std < self.flatline_std_uv:
            flags.append("flatline")

        # Rough EMG proxy: share of spectral energy above hf_cutoff_hz.
        if channel.size >= 16:
            spectrum = np.abs(np.fft.rfft(channel - channel.mean()))
            freqs = np.fft.rfftfreq(channel.size, d=1.0 / sample_rate_hz)
            total = float(np.sum(spectrum) + 1e-12)
            hf = float(np.sum(spectrum[freqs >= self.hf_cutoff_hz]))
            if (hf / total) > self.hf_ratio_threshold:
                flags.append("high_frequency")
        return flags
