"""Helpers to train and export the default sklearn intent model."""

from __future__ import annotations

from pathlib import Path

from sklearn.model_selection import cross_val_score

from bci_iot.ml.dataset import make_synthetic_feature_dataset
from bci_iot.ml.sklearn_classifier import SklearnIntentClassifier


def train_default_classifier(
    *,
    n_samples: int = 300,
    seed: int = 42,
    model_path: Path | str | None = None,
) -> tuple[SklearnIntentClassifier, float]:
    """Train on synthetic features and optionally save the model.

    Returns:
        The fitted classifier and mean 5-fold accuracy on the training set.
    """

    features, labels = make_synthetic_feature_dataset(n_samples=n_samples, seed=seed)
    classifier = SklearnIntentClassifier()
    scores = cross_val_score(classifier._model, features, labels, cv=5)
    mean_accuracy = float(scores.mean())
    classifier.fit(features, labels)
    if model_path is not None:
        classifier.save(model_path)
    return classifier, mean_accuracy
