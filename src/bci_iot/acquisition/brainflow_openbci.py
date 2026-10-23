"""BrainFlow OpenBCI boards (Cyton / Ganglion) with safe synthetic fallback."""

from __future__ import annotations

import os
import time
from collections.abc import Iterator

import numpy as np

from bci_iot.acquisition.base import EEGSource
from bci_iot.acquisition.brainflow_source import BrainFlowSyntheticSource, brainflow_available
from bci_iot.types import EEGWindow

# 10–20 labels used by Iris (Cyton 8 ch map — docs/HARDWARE_CUFFIA.md)
DEFAULT_CHANNEL_NAMES = ("Fp1", "Fp2", "F3", "F4", "C3", "Cz", "C4", "Pz")


def openbci_env_board() -> str:
    """``cyton`` | ``ganglion`` | ``synthetic`` | ``auto`` from env."""
    return (os.getenv("BCI_IOT_BRAINFLOW_BOARD") or "auto").strip().lower()


def openbci_serial_port() -> str:
    return (os.getenv("BCI_IOT_BRAINFLOW_SERIAL_PORT") or "").strip()


def openbci_mac_address() -> str:
    return (os.getenv("BCI_IOT_BRAINFLOW_MAC") or "").strip()


def resolve_openbci_board_id(board: str) -> int:
    from brainflow.board_shim import BoardIds

    name = (board or "cyton").strip().lower()
    if name in {"cyton", "openbci", "cyton_board"}:
        return int(BoardIds.CYTON_BOARD.value)
    if name in {"ganglion", "ganglion_board"}:
        return int(BoardIds.GANGLION_BOARD.value)
    if name in {"synthetic", "synthetic_board"}:
        return int(BoardIds.SYNTHETIC_BOARD.value)
    raise ValueError(f"Unsupported OpenBCI board={board!r} (use cyton|ganglion|synthetic)")


class BrainFlowOpenBciSource(EEGSource):
    """Stream windows from a physical OpenBCI board via BrainFlow.

    Requires ``brainflow`` and a connected board (serial COM port on Windows for
    Cyton dongle). Prefer env:

    - ``BCI_IOT_BRAINFLOW_BOARD=cyton``
    - ``BCI_IOT_BRAINFLOW_SERIAL_PORT=COM3``
    """

    def __init__(
        self,
        *,
        board: str = "cyton",
        serial_port: str = "",
        mac_address: str = "",
        window_seconds: float = 1.0,
        n_channels: int | None = None,
        max_windows: int | None = None,
        poll_interval_s: float = 0.05,
        settle_s: float = 0.5,
    ) -> None:
        if not brainflow_available():
            raise ImportError(
                "brainflow is not installed. Run: pip install -e \".[acquisition]\""
            )
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")

        from brainflow.board_shim import BoardShim, BrainFlowInputParams

        self._BoardShim = BoardShim
        self.board_name = board.strip().lower() or "cyton"
        self._board_id = resolve_openbci_board_id(self.board_name)
        self.window_seconds = window_seconds
        self.max_windows = max_windows
        self.poll_interval_s = poll_interval_s
        self.settle_s = settle_s

        params = BrainFlowInputParams()
        port = (serial_port or openbci_serial_port()).strip()
        mac = (mac_address or openbci_mac_address()).strip()
        if port:
            params.serial_port = port
        if mac:
            params.mac_address = mac
        self._params = params
        self._serial_port = port
        self._mac = mac

        self.sample_rate_hz = float(BoardShim.get_sampling_rate(self._board_id))
        eeg_channels = list(BoardShim.get_eeg_channels(self._board_id))
        if n_channels is not None:
            if n_channels < 1 or n_channels > len(eeg_channels):
                raise ValueError(
                    f"n_channels must be in 1..{len(eeg_channels)} for board {self.board_name}"
                )
            self._eeg_channels = eeg_channels[:n_channels]
        else:
            self._eeg_channels = eeg_channels

        self.n_channels = len(self._eeg_channels)
        self.n_samples = int(round(self.sample_rate_hz * window_seconds))
        names = DEFAULT_CHANNEL_NAMES[: self.n_channels]
        if len(names) < self.n_channels:
            names = names + tuple(f"Ch{i + 1}" for i in range(len(names), self.n_channels))
        self._channel_names = names
        self._board: BoardShim | None = None
        self._running = False

    def start(self) -> None:
        if self._board is not None:
            return
        if self.board_name not in {"synthetic", "synthetic_board"} and not self._serial_port and not self._mac:
            raise RuntimeError(
                "OpenBCI: imposta BCI_IOT_BRAINFLOW_SERIAL_PORT (es. COM3) "
                "o BCI_IOT_BRAINFLOW_MAC per Ganglion BLE."
            )
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
            raise RuntimeError("BrainFlowOpenBciSource must be started before iterating")

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
        deadline = time.perf_counter() + max(3.0, self.window_seconds * 6)
        while time.perf_counter() < deadline:
            data = self._board.get_current_board_data(n_samples)
            if data.shape[1] >= n_samples:
                return data
            time.sleep(self.poll_interval_s)
        raise TimeoutError(
            f"OpenBCI {self.board_name} non ha fornito {n_samples} campioni in tempo"
        )


def capture_one_openbci_window(
    *,
    board: str | None = None,
    window_seconds: float = 1.0,
    n_channels: int = 8,
    fallback_synthetic: bool = True,
) -> tuple[EEGWindow, str]:
    """One window from Cyton (or env board). Falls back to SyntheticBoard if asked."""

    chosen = (board or openbci_env_board() or "cyton").strip().lower()
    if chosen in {"auto", ""}:
        chosen = "cyton" if openbci_serial_port() or openbci_mac_address() else "synthetic"

    if chosen in {"synthetic", "synthetic_board"}:
        src = BrainFlowSyntheticSource(
            window_seconds=window_seconds, n_channels=n_channels, max_windows=1
        )
        with src:
            windows = list(src.iter_windows())
        if not windows:
            raise RuntimeError("SyntheticBoard: nessuna finestra")
        return windows[0], "brainflow_synthetic"

    try:
        src = BrainFlowOpenBciSource(
            board=chosen,
            window_seconds=window_seconds,
            n_channels=n_channels,
            max_windows=1,
        )
        with src:
            windows = list(src.iter_windows())
        if not windows:
            raise RuntimeError(f"OpenBCI {chosen}: nessuna finestra")
        return windows[0], "brainflow_openbci"
    except Exception:
        if not fallback_synthetic:
            raise
        src = BrainFlowSyntheticSource(
            window_seconds=window_seconds, n_channels=n_channels, max_windows=1
        )
        with src:
            windows = list(src.iter_windows())
        if not windows:
            raise RuntimeError("Fallback SyntheticBoard: nessuna finestra") from None
        return windows[0], "brainflow_synthetic_fallback"


def probe_openbci_connection() -> dict[str, object]:
    """Health check for Config / lab UI."""

    if not brainflow_available():
        return {
            "ok": False,
            "mode": "unavailable",
            "detail": "brainflow non installato (pip install -e \".[acquisition]\")",
        }
    board = openbci_env_board()
    port = openbci_serial_port()
    try:
        window, path = capture_one_openbci_window(
            board=None if board == "auto" else board,
            window_seconds=0.5,
            n_channels=4,
            fallback_synthetic=True,
        )
        return {
            "ok": True,
            "mode": path,
            "board_env": board,
            "serial_port": port or "",
            "detail": f"Stream ok via {path}",
            "channels": int(window.data.shape[0]),
            "samples": int(window.data.shape[1]),
            "sample_rate_hz": float(window.sample_rate_hz),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "mode": "openbci",
            "board_env": board,
            "serial_port": port or "",
            "detail": str(exc)[:240],
        }
