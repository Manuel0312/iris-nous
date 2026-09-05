"""Train a tiny classifier on literature-prior windows (coherent demo ML)."""

from __future__ import annotations

import numpy as np

from bci_iot.acquisition.priors import COMMAND_PRIORS, synthesize_prior_window
from bci_iot.ml.sklearn_classifier import SklearnIntentClassifier
from bci_iot.preprocessing.features import BandPowerExtractor


def train_prior_impulse_classifier(
    *,
    samples_per_command: int = 40,
    seed: int = 7,
) -> SklearnIntentClassifier:
    """Fit sklearn on features extracted from literature spectral priors."""

    extractor = BandPowerExtractor(notch_hz=None)
    rng = np.random.default_rng(seed)
    xs: list[np.ndarray] = []
    ys: list[str] = []

    for command, prior in COMMAND_PRIORS.items():
        for i in range(samples_per_command):
            window = synthesize_prior_window(
                command,
                seed=int(rng.integers(0, 1_000_000)),
            )
            features = extractor.transform(window)
            xs.append(features.values.copy())
            ys.append(prior.intent.value)

    x = np.vstack(xs)
    y = np.array(ys, dtype=object)
    clf = SklearnIntentClassifier()
    clf.fit(x, y)
    return clf
