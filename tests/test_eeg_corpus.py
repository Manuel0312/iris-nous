"""Vendored PhysioNet EEG corpus for headset impulses."""

from __future__ import annotations

from bci_iot.acquisition.eeg_corpus import (
    blend_prior_on_real,
    corpus_available,
    corpus_meta,
    sample_physionet_window,
    window_compact_stats,
)


def test_physionet_corpus_loads() -> None:
    assert corpus_available() is True
    meta = corpus_meta()
    assert meta["n_windows"] >= 8
    assert meta["sample_rate_hz"] == 160.0
    assert "physionet" in meta["source"]

    window = sample_physionet_window(n_channels=8, seed=3)
    assert window is not None
    assert window.data.shape == (8, 160)
    blended = blend_prior_on_real(window, "ACCENDI", seed=5)
    assert blended.data.shape == window.data.shape
    stats = window_compact_stats(blended)
    assert stats["n_channels"] == 8
    assert len(stats["rms"]) == 8
