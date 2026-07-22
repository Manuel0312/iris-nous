"""Literature-backed EEG spectral priors for command-like mental states.

Important honesty for the thesis
--------------------------------
There is **no** free public table of Italian words ``ACCENDI`` / ``SPEGNI`` /
``RISPONDI`` mapped to exact microvolt EEG templates. What *does* exist:

1. **Imagined-speech corpora** (same *paradigm* as your calibration idea):
   - Pressel et al. 2016/2017 — 15 subjects, Spanish vowels + directional
     commands (arriba, adelante, …), open on Zenodo / MOABB ``Pressel2016``.
   - Other MOABB imagined-speech sets (Nieto2022, AguileraRodriguez2025, …).

2. **Relax vs focus / meditation** spectral facts (alpha ↑ when relaxed,
   beta ↑ when attentive), used in countless BCI papers and public Muse /
   Emotiv relax–concentration datasets (e.g. Mendeley “Fusion relaxation and
   concentration moods”).

This module encodes **those public spectral priors** as synthesizable EEG
windows so the simulator is coherent with literature, not random noise.
Italian command words are *labels we attach* to those scientifically grounded
states (to be replaced later by per-user calibration or MoABB trials).

References (URLs)
-----------------
- Pressel imagined speech: https://zenodo.org/records/19502780
- MOABB dataset summary: https://moabb.neurotechx.com/docs/dataset_summary.html
- Alpha ~8–12 Hz relaxation / Beta ~13–30 Hz attention: standard EEG bands
  (also Muse dataset docs on Zenodo 8429740).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from bci_iot.types import EEGWindow, IntentLabel


@dataclass(frozen=True, slots=True)
class SpectralPrior:
    """Band-power oriented prior for one mental command class."""

    command: str
    intent: IntentLabel
    description: str
    # Dominant oscillations (Hz, relative amplitude)
    tones_hz: tuple[tuple[float, float], ...]
    noise_std: float
    source_note: str


# Public-prior library used by the impulse simulator + demo UI.
COMMAND_PRIORS: dict[str, SpectralPrior] = {
    "SPEGNI": SpectralPrior(
        command="SPEGNI",
        intent=IntentLabel.RELAX,
        description="Stato rilassato / ‘spegni’: alpha dominante (8–12 Hz).",
        tones_hz=((10.0, 1.0), (9.0, 0.45), (20.0, 0.15)),
        noise_std=0.25,
        source_note="Alpha↑ relax (letteratura EEG + dataset relax/concentration pubblici).",
    ),
    "ACCENDI": SpectralPrior(
        command="ACCENDI",
        intent=IntentLabel.FOCUS,
        description="Attenzione / ‘accendi’: beta più forte (13–30 Hz).",
        tones_hz=((18.0, 1.0), (22.0, 0.55), (10.0, 0.2)),
        noise_std=0.3,
        source_note="Beta↑ attention/focus (stesse fonti spectral pubbliche).",
    ),
    "RISPONDI": SpectralPrior(
        command="RISPONDI",
        intent=IntentLabel.ACCEPT,
        description="Decisione / ‘rispondi’: mix alpha–beta (cue di risposta).",
        tones_hz=((12.0, 0.7), (16.0, 0.85), (8.0, 0.35)),
        noise_std=0.28,
        source_note=(
            "Paradigma tipo imagined-speech / decision cue "
            "(MOABB Pressel2016: comandi immaginati; qui prior spettrale)."
        ),
    ),
    "RIFIUTA": SpectralPrior(
        command="RIFIUTA",
        intent=IntentLabel.REJECT,
        description="Rifiuto: beta medio-alto + meno alpha.",
        tones_hz=((24.0, 0.9), (15.0, 0.5), (9.0, 0.15)),
        noise_std=0.3,
        source_note="Variant attentiva distinta da RISPONDI (prior demo documentato).",
    ),
}


def synthesize_prior_window(
    command: str,
    *,
    sample_rate_hz: float = 250.0,
    n_channels: int = 8,
    window_seconds: float = 1.0,
    seed: int | None = None,
) -> EEGWindow:
    """Build a multi-channel EEG window from a literature spectral prior."""

    key = command.strip().upper()
    if key not in COMMAND_PRIORS:
        raise KeyError(f"Unknown command {command!r}. Choose from {sorted(COMMAND_PRIORS)}")

    prior = COMMAND_PRIORS[key]
    rng = np.random.default_rng(seed)
    n_samples = int(round(sample_rate_hz * window_seconds))
    t = np.arange(n_samples, dtype=np.float64) / sample_rate_hz

    channels: list[NDArray[np.floating[Any]]] = []
    for ch in range(n_channels):
        signal = np.zeros(n_samples, dtype=np.float64)
        phase = rng.uniform(0, 2 * np.pi)
        for freq, amp in prior.tones_hz:
            # Mild channel-wise amplitude jitter (inter-subject variability proxy).
            a = amp * (0.85 + 0.3 * rng.random())
            signal += a * np.sin(2 * np.pi * freq * t + phase + 0.1 * ch)
        signal += rng.normal(0.0, prior.noise_std, size=n_samples)
        channels.append(signal)

    data = np.vstack(channels) * 20.0  # scale to tens of µV-like units
    return EEGWindow(
        data=data,
        sample_rate_hz=sample_rate_hz,
        timestamp_s=0.0,
        channel_names=tuple(f"CH{i + 1}" for i in range(n_channels)),
    )


def list_demo_commands() -> list[dict[str, str]]:
    """UI-friendly list of commands and short explanations."""

    return [
        {
            "command": p.command,
            "intent": p.intent.value,
            "description": p.description,
            "source_note": p.source_note,
        }
        for p in COMMAND_PRIORS.values()
    ]
