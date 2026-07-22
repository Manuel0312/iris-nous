"""Zero-cost EEG simulator used before physical headset integration.

This is a lightweight stand-in for BrainFlow ``SyntheticBoard``. It does not
require the ``brainflow`` package so local tests run offline. A future
``BrainFlowSyntheticSource`` can wrap the real board behind the same interface.
"""

from __future__ import annotations

import time
from collections.abc import Iterator

import numpy as np

from bci_iot.acquisition.base import EEGSource
from bci_iot.types import EEGWindow


class SyntheticEEGSource(EEGSource):
    """Generate band-limited noise windows shaped like multi-channel EEG."""

    def __init__(
        self,
        *,
        sample_rate_hz: float = 250.0,
        n_channels: int = 8,
        window_seconds: float = 1.0,
        seed: int | None = 42,
        max_windows: int | None = None,
        realtime: bool = False,
    ) -> None:
        if sample_rate_hz <= 0 or n_channels <= 0 or window_seconds <= 0:
            raise ValueError("sample_rate_hz, n_channels and window_seconds must be positive")
        self.sample_rate_hz = sample_rate_hz
        self.n_channels = n_channels
        self.window_seconds = window_seconds
        self.n_samples = int(round(sample_rate_hz * window_seconds))
        self.max_windows = max_windows
        self.realtime = realtime
        self._rng = np.random.default_rng(seed)
        self._running = False
        self._channel_names = tuple(f"CH{i + 1}" for i in range(n_channels))

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def iter_windows(self) -> Iterator[EEGWindow]:
        if not self._running:
            raise RuntimeError("SyntheticEEGSource must be started before iterating")

        produced = 0
        t0 = time.perf_counter()
        while self._running:
            if self.max_windows is not None and produced >= self.max_windows:
                break

            # Colored-ish noise: smooth random walk per channel (µV-scale amplitudes).
            white = self._rng.normal(0.0, 1.0, size=(self.n_channels, self.n_samples))
            data = np.cumsum(white, axis=1)
            data = data - data.mean(axis=1, keepdims=True)
            data = data * 5.0  # keep synthetic amplitudes in a mild µV-like range

            timestamp_s = time.perf_counter() - t0
            yield EEGWindow(
                data=data.astype(np.float64),
                sample_rate_hz=self.sample_rate_hz,
                timestamp_s=timestamp_s,
                channel_names=self._channel_names,
            )
            produced += 1

            if self.realtime:
                time.sleep(self.window_seconds)
