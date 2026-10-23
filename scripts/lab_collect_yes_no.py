#!/usr/bin/env python3
"""Lab: collect SÌ / NO / riposo EEG windows (HARDWARE_CUFFIA fase B).

Uses OpenBCI Cyton when BCI_IOT_BRAINFLOW_SERIAL_PORT is set, otherwise
BrainFlow SyntheticBoard / NumPy fallback. Applies notch 50 Hz + bandpass 1–40 Hz.

Example:
  .\\.venv\\Scripts\\python.exe scripts\\lab_collect_yes_no.py --out data\\lab_sessions
"""

from __future__ import annotations

import argparse
import csv
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from bci_iot.acquisition.brainflow_openbci import capture_one_openbci_window
from bci_iot.acquisition.brainflow_source import brainflow_available
from bci_iot.acquisition.synthetic import SyntheticEEGSource
from bci_iot.preprocessing.filters import bandpass_filter, notch_filter


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _capture(label: str, n_channels: int, window_seconds: float) -> tuple[np.ndarray, float, str]:
    if brainflow_available():
        window, path = capture_one_openbci_window(
            window_seconds=window_seconds,
            n_channels=n_channels,
            fallback_synthetic=True,
        )
        return window.data, float(window.sample_rate_hz), path
    src = SyntheticEEGSource(
        sample_rate_hz=250.0,
        n_channels=n_channels,
        window_seconds=window_seconds,
        max_windows=1,
        seed=int(time.time()) % 1_000_000,
    )
    with src:
        windows = list(src.iter_windows())
    if not windows:
        raise RuntimeError("SyntheticEEGSource: nessuna finestra")
    w = windows[0]
    return w.data, float(w.sample_rate_hz), f"numpy_synthetic:{label}"


def _clean(data: np.ndarray, fs: float) -> np.ndarray:
    x = notch_filter(data, sample_rate_hz=fs, notch_hz=50.0)
    return bandpass_filter(x, sample_rate_hz=fs, low_hz=1.0, high_hz=40.0)


def _write_csv(path: Path, data: np.ndarray, fs: float, label: str, source: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    n_ch, n_samp = data.shape
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["label", label, "sample_rate_hz", fs, "source", source, "channels", n_ch])
        header = ["t_s"] + [f"ch{i + 1}" for i in range(n_ch)]
        w.writerow(header)
        for i in range(n_samp):
            t = i / fs
            row = [f"{t:.6f}"] + [f"{float(data[c, i]):.8f}" for c in range(n_ch)]
            w.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser(description="Raccolta lab SÌ/NO/riposo EEG")
    parser.add_argument("--out", type=Path, default=Path("data/lab_sessions"))
    parser.add_argument("--channels", type=int, default=8)
    parser.add_argument("--window", type=float, default=2.0, help="secondi per finestra")
    parser.add_argument("--repeats", type=int, default=3, help="finestre per etichetta")
    args = parser.parse_args()

    session = args.out / _utc_stamp()
    session.mkdir(parents=True, exist_ok=True)
    print(f"Sessione: {session}")
    print("Ordine: SI → NO → RIPOSO. Premi Invio a ogni passo.")

    labels = ("SI", "NO", "RIPOSO")
    for label in labels:
        input(f"\nPensa «{label}» e premi Invio per catturare {args.repeats} finestre… ")
        for n in range(1, args.repeats + 1):
            raw, fs, source = _capture(label, args.channels, args.window)
            cleaned = _clean(raw, fs)
            out = session / f"{label.lower()}_{n:02d}.csv"
            _write_csv(out, cleaned, fs, label, source)
            print(f"  salvato {out.name}  source={source}  shape={cleaned.shape}")

    meta = session / "README.txt"
    meta.write_text(
        "Lab Iris — CSV filtrati (notch 50 Hz, bandpass 1–40 Hz).\n"
        "Con Cyton: BCI_IOT_BRAINFLOW_BOARD=cyton e BCI_IOT_BRAINFLOW_SERIAL_PORT=COMx\n",
        encoding="utf-8",
    )
    print(f"\nFatto. Cartella: {session}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
