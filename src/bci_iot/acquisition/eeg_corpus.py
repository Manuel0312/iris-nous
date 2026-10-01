"""Vendored public EEG windows for headset impulses (PhysioNet MMIDB).

Source
------
PhysioNet EEG Motor Movement/Imagery Dataset (eegmmidb) 1.0.0, subject S001
run R01 (eyes-open baseline). License: ODC-BY-1.0.
https://physionet.org/content/eegmmidb/1.0.0/

We ship a compact NPZ of 1-second, 8-channel windows extracted from that
recording so impulses feel like real scalp EEG rather than literary priors alone.
Command-specific spectral priors are lightly blended on top for intent colouring
when BrainFlow is unavailable.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

from bci_iot.acquisition.priors import COMMAND_PRIORS, synthesize_prior_window
from bci_iot.types import EEGWindow

CORPUS_FILENAME = "physionet_mmidb_s001r01_windows.npz"
CORPUS_DIR = Path(__file__).resolve().parent / "data"
MIN_IMPULSES_FOR_READY = 3


@lru_cache(maxsize=1)
def _load_corpus() -> dict[str, Any] | None:
    path = CORPUS_DIR / CORPUS_FILENAME
    if not path.is_file():
        return None
    try:
        with np.load(path, allow_pickle=False) as z:
            windows = np.asarray(z["windows"], dtype=np.float64)
            sr = float(np.asarray(z["sample_rate_hz"]).item())
            names = tuple(str(x) for x in np.asarray(z["channel_names"]).tolist())
            source = str(np.asarray(z["source"]).item())
            url = str(np.asarray(z["url"]).item()) if "url" in z.files else ""
        if windows.ndim != 3 or windows.shape[0] < 1:
            return None
        return {
            "windows": windows,
            "sample_rate_hz": sr,
            "channel_names": names,
            "source": source,
            "url": url,
            "path": str(path),
        }
    except (OSError, ValueError, KeyError):
        return None


def corpus_available() -> bool:
    return _load_corpus() is not None


def corpus_meta() -> dict[str, Any]:
    data = _load_corpus()
    if data is None:
        return {"available": False}
    return {
        "available": True,
        "source": data["source"],
        "url": data["url"],
        "n_windows": int(data["windows"].shape[0]),
        "n_channels": int(data["windows"].shape[1]),
        "n_samples": int(data["windows"].shape[2]),
        "sample_rate_hz": data["sample_rate_hz"],
        "channel_names": list(data["channel_names"]),
    }


def sample_physionet_window(
    *,
    n_channels: int = 8,
    seed: int | None = None,
    window_index: int | None = None,
) -> EEGWindow | None:
    """Return one 1s window from the vendored PhysioNet corpus."""

    data = _load_corpus()
    if data is None:
        return None
    rng = np.random.default_rng(seed)
    n_win = int(data["windows"].shape[0])
    idx = int(window_index) if window_index is not None else int(rng.integers(0, n_win))
    idx = idx % n_win
    block = np.asarray(data["windows"][idx], dtype=np.float64)
    # Match requested channel count (tile/truncate).
    if block.shape[0] >= n_channels:
        block = block[:n_channels]
        names = data["channel_names"][:n_channels]
    else:
        reps = int(np.ceil(n_channels / block.shape[0]))
        block = np.tile(block, (reps, 1))[:n_channels]
        names = tuple(f"CH{i + 1}" for i in range(n_channels))
    return EEGWindow(
        data=block,
        sample_rate_hz=float(data["sample_rate_hz"]),
        timestamp_s=0.0,
        channel_names=tuple(names),
    )


def blend_prior_on_real(
    real: EEGWindow,
    command: str,
    *,
    seed: int | None = None,
    prior_weight: float = 0.28,
) -> EEGWindow:
    """Keep PhysioNet morphology; tint with a literature spectral prior for intent."""

    key = command.strip().upper()
    if key not in COMMAND_PRIORS:
        return real
    prior = synthesize_prior_window(
        key,
        sample_rate_hz=real.sample_rate_hz,
        n_channels=real.data.shape[0],
        window_seconds=real.data.shape[1] / real.sample_rate_hz,
        seed=seed,
    )
    # Resample prior length if needed.
    if prior.data.shape[1] != real.data.shape[1]:
        # Simple truncate/pad.
        n = real.data.shape[1]
        if prior.data.shape[1] >= n:
            pdata = prior.data[:, :n]
        else:
            pad = n - prior.data.shape[1]
            pdata = np.pad(prior.data, ((0, 0), (0, pad)))
    else:
        pdata = prior.data
    # Scale prior to real RMS so blend stays in µV-like range.
    real_rms = float(np.sqrt(np.mean(real.data**2)) or 1.0)
    prior_rms = float(np.sqrt(np.mean(pdata**2)) or 1.0)
    pdata = pdata * (real_rms / prior_rms)
    w = float(np.clip(prior_weight, 0.0, 0.6))
    mixed = (1.0 - w) * real.data + w * pdata
    return EEGWindow(
        data=mixed.astype(np.float64),
        sample_rate_hz=real.sample_rate_hz,
        timestamp_s=real.timestamp_s,
        channel_names=real.channel_names,
    )


def window_compact_stats(window: EEGWindow) -> dict[str, Any]:
    """Small JSON-friendly summary stored with each impulse for later ops."""

    data = window.data
    return {
        "n_channels": int(data.shape[0]),
        "n_samples": int(data.shape[1]),
        "sample_rate_hz": float(window.sample_rate_hz),
        "rms": [round(float(np.sqrt(np.mean(ch**2))), 4) for ch in data],
        "mean": [round(float(np.mean(ch)), 4) for ch in data],
        "channel_names": list(window.channel_names),
    }
