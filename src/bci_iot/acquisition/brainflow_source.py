"""BrainFlow SyntheticBoard EEG source (zero-cost, same API as real boards)."""

from __future__ import annotations

import time
from collections.abc import Iterator

import numpy as np

from bci_iot.acquisition.base import EEGSource
from bci_iot.types import EEGWindow


def brainflow_available() -> bool:
    """Return True if the ``brainflow`` package can be imported."""

    try:
        import brainflow  # noqa: F401
    except ImportError:
        return False
    return True


class BrainFlowSyntheticSource(EEGSource):
    """Stream windows from BrainFlow ``SYNTHETIC_BOARD``.

    Uses the same BrainFlow API that a physical headset board would use, so the
    rest of the pipeline can switch to hardware later without redesign.
    """

    def __init__(
        self,
        *,
        window_seconds: float = 1.0,
        n_channels: int | None = None,
        max_windows: int | None = None,
        poll_interval_s: float = 0.05,
        settle_s: float = 0.3,
    ) -> None:
        if not brainflow_available():
            raise ImportError(
                "brainflow is not installed. Run: pip install -e \".[acquisition]\""
            )
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")

        from brainflow.board_shim import BoardIds, BoardShim, BrainFlowInputParams

        self._BoardShim = BoardShim
        self._board_id = BoardIds.SYNTHETIC_BOARD.value
        self.window_seconds = window_seconds
        self.max_windows = max_windows
        self.poll_interval_s = poll_interval_s
        self.settle_s = settle_s

        self.sample_rate_hz = float(BoardShim.get_sampling_rate(self._board_id))
        eeg_channels = BoardShim.get_eeg_channels(self._board_id)
        if n_channels is not None:
            if n_channels < 1 or n_channels > len(eeg_channels):
                raise ValueError(
                    f"n_channels must be in 1..{len(eeg_channels)} for SyntheticBoard"
                )
            self._eeg_channels = eeg_channels[:n_channels]
        else:
            self._eeg_channels = eeg_channels

        self.n_channels = len(self._eeg_channels)
        self.n_samples = int(round(self.sample_rate_hz * window_seconds))
        self._channel_names = tuple(f"BF{ch}" for ch in self._eeg_channels)
        self._params = BrainFlowInputParams()
        self._board: BoardShim | None = None
        self._running = False

    def start(self) -> None:
        if self._board is not None:
            return
        board = self._BoardShim(self._board_id, self._params)
        board.prepare_session()
        board.start_stream()
        time.sleep(self.settle_s)
        self._board = board
        self._running = True

    def stop(self) -> None:
        self._running = False
        board = self._board
        self._board = None
        if board is None:
            return
        try:
            board.stop_stream()
        finally:
            board.release_session()

    def iter_windows(self) -> Iterator[EEGWindow]:
        if self._board is None or not self._running:
            raise RuntimeError("BrainFlowSyntheticSource must be started before iterating")

        produced = 0
        t0 = time.perf_counter()
        while self._running:
            if self.max_windows is not None and produced >= self.max_windows:
                break

            data = self._wait_for_samples(self.n_samples)
            eeg = data[self._eeg_channels, -self.n_samples :].astype(np.float64)
            yield EEGWindow(
                data=eeg,
                sample_rate_hz=self.sample_rate_hz,
                timestamp_s=time.perf_counter() - t0,
                channel_names=self._channel_names,
            )
            produced += 1

    def _wait_for_samples(self, n_samples: int) -> np.ndarray:
        assert self._board is not None
        deadline = time.perf_counter() + max(2.0, self.window_seconds * 4)
        while time.perf_counter() < deadline:
            data = self._board.get_current_board_data(n_samples)
            if data.shape[1] >= n_samples:
                return data
            time.sleep(self.poll_interval_s)
        raise TimeoutError(
            f"BrainFlow SyntheticBoard did not provide {n_samples} samples in time"
        )
