"""Synthetic labeled feature sets for offline classifier training."""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from bci_iot.types import IntentLabel


def make_synthetic_feature_dataset(
    n_samples: int = 200,
    *,
    seed: int = 42,
) -> tuple[NDArray[np.floating[Any]], NDArray[Any]]:
    """Create a separable Alpha/Beta feature dataset for FOCUS vs RELAX.

    RELAX samples have higher ``alpha_beta_ratio``; FOCUS samples have lower
    ratios. A small IDLE cluster sits near the decision boundary.
    """

    if n_samples < 6:
        raise ValueError("n_samples must be >= 6")

    rng = np.random.default_rng(seed)
    n_relax = n_samples // 3
    n_focus = n_samples // 3
    n_idle = n_samples - n_relax - n_focus

    def _block(n: int, ratio_mean: float, ratio_std: float, label: str) -> tuple[np.ndarray, np.ndarray]:
        ratio = rng.normal(ratio_mean, ratio_std, size=n)
        alpha = rng.normal(1.0 if label == IntentLabel.RELAX.value else 0.2, 0.15, size=n)
        beta = rng.normal(0.2 if label == IntentLabel.RELAX.value else 1.0, 0.15, size=n)
        x = np.column_stack([alpha, beta, ratio]).astype(np.float64)
        y = np.array([label] * n, dtype=object)
        return x, y

    x_r, y_r = _block(n_relax, ratio_mean=1.8, ratio_std=0.25, label=IntentLabel.RELAX.value)
    x_f, y_f = _block(n_focus, ratio_mean=0.4, ratio_std=0.2, label=IntentLabel.FOCUS.value)
    x_i, y_i = _block(n_idle, ratio_mean=1.0, ratio_std=0.08, label=IntentLabel.IDLE.value)

    features = np.vstack([x_r, x_f, x_i])
    labels = np.concatenate([y_r, y_f, y_i])
    order = rng.permutation(features.shape[0])
    return features[order], labels[order]
