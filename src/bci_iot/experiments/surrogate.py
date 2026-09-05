"""Build a MoABB-*paradigm* surrogate dataset without downloading GB of EEG.

Honesty for the thesis
----------------------
Real MoABB corpora (e.g. Pressel2016 imagined speech) require the optional
``moabb`` extra and a first-time download. Until then we evaluate the *same
pipeline* (band-power features → logistic regression) on windows synthesized
from the public spectral priors documented in ``docs/EEG_PRIORS.md``.

This is **not** claimed as accuracy on Pressel subjects; it is a reproducible
baseline that proves the software chain and leaves a drop-in hook for real MoABB
epochs (see ``moabb_loader.py``).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from bci_iot.acquisition.priors import COMMAND_PRIORS, synthesize_prior_window
from bci_iot.preprocessing.features import BandPowerExtractor
from bci_iot.types import IntentLabel


# Four classes aligned with Voilà colour calibration / folders.
SURROGATE_COMMANDS: tuple[str, ...] = ("ACCENDI", "RISPONDI", "RIFIUTA", "SPEGNI")


@dataclass(frozen=True, slots=True)
class SurrogateBundle:
    """Feature matrix + labels + subject ids for LOSO / k-fold."""

    features: NDArray[np.floating]
    labels: NDArray[object]
    subjects: NDArray[np.int_]
    command_names: tuple[str, ...]
    note: str


def build_surrogate_bundle(
    *,
    n_subjects: int = 8,
    windows_per_class: int = 12,
    seed: int = 42,
) -> SurrogateBundle:
    """Synthesize multi-subject imagined-command windows → α/β features."""

    if n_subjects < 2:
        raise ValueError("n_subjects must be >= 2 for leave-one-subject-out")
    extractor = BandPowerExtractor(notch_hz=None)
    rng = np.random.default_rng(seed)

    rows: list[NDArray[np.floating]] = []
    labels: list[str] = []
    subjects: list[int] = []

    for subject in range(n_subjects):
        # Per-subject seed shift ≈ inter-individual variability
        subject_seed = int(rng.integers(0, 1_000_000))
        for command in SURROGATE_COMMANDS:
            intent = COMMAND_PRIORS[command].intent.value
            for i in range(windows_per_class):
                window = synthesize_prior_window(
                    command,
                    seed=subject_seed + i * 17 + hash(command) % 997,
                )
                feat = extractor.transform(window)
                rows.append(feat.values.copy())
                labels.append(intent)
                subjects.append(subject)

    return SurrogateBundle(
        features=np.vstack(rows),
        labels=np.array(labels, dtype=object),
        subjects=np.asarray(subjects, dtype=np.int_),
        command_names=SURROGATE_COMMANDS,
        note=(
            "Surrogate MoABB-paradigm dataset from literature spectral priors "
            "(not real Pressel EEG). Optional: pip install -e \".[experiments]\" "
            "and use --mode moabb when a dataset loader is available."
        ),
    )


def intent_order() -> list[IntentLabel]:
    return [
        IntentLabel.FOCUS,
        IntentLabel.ACCEPT,
        IntentLabel.REJECT,
        IntentLabel.RELAX,
    ]
