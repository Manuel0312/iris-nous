"""Tests for the trainable sklearn intent classifier."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from bci_iot.ml import SklearnIntentClassifier, train_default_classifier
from bci_iot.types import FeatureVector, IntentLabel


def test_train_predict_and_persist(tmp_path: Path) -> None:
    model_path = tmp_path / "baseline.joblib"
    classifier, accuracy = train_default_classifier(n_samples=120, seed=0, model_path=model_path)
    assert classifier.is_fitted
    assert accuracy > 0.8
    assert model_path.exists()

    loaded = SklearnIntentClassifier.load(model_path)
    focus = FeatureVector(
        values=np.array([0.2, 1.0, 0.3], dtype=np.float64),
        names=("alpha_logpower", "beta_logpower", "alpha_beta_ratio"),
        timestamp_s=1.0,
    )
    relax = FeatureVector(
        values=np.array([1.0, 0.2, 1.9], dtype=np.float64),
        names=("alpha_logpower", "beta_logpower", "alpha_beta_ratio"),
        timestamp_s=2.0,
    )
    assert loaded.predict(focus).label == IntentLabel.FOCUS
    assert loaded.predict(relax).label == IntentLabel.RELAX


def test_dirty_features_yield_idle() -> None:
    classifier, _ = train_default_classifier(n_samples=90, seed=1)
    dirty = FeatureVector(
        values=np.array([1.0, 1.0, 1.0], dtype=np.float64),
        names=("alpha_logpower", "beta_logpower", "alpha_beta_ratio"),
        timestamp_s=0.0,
        is_clean=False,
        artifact_flags=("window:too_many_bad_channels",),
    )
    intent = classifier.predict(dirty)
    assert intent.label == IntentLabel.IDLE
    assert intent.confidence == 0.0
