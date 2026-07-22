"""Machine-learning intent classification."""

from __future__ import annotations

from bci_iot.ml.calibrate import calibrate_user_model
from bci_iot.ml.base import IntentClassifier
from bci_iot.ml.dataset import make_synthetic_feature_dataset
from bci_iot.ml.heuristic import HeuristicIntentClassifier
from bci_iot.ml.sklearn_classifier import SklearnIntentClassifier
from bci_iot.ml.train import train_default_classifier

__all__ = [
    "HeuristicIntentClassifier",
    "IntentClassifier",
    "SklearnIntentClassifier",
    "calibrate_user_model",
    "make_synthetic_feature_dataset",
    "train_default_classifier",
]
