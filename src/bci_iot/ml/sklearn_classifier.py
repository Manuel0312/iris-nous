"""Trainable scikit-learn intent classifier with joblib persistence."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
from numpy.typing import NDArray
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from bci_iot.types import ClassifiedIntent, FeatureVector, IntentLabel


class SklearnIntentClassifier:
    """Logistic-regression head on standardized band-power features.

    This is the first real ML module of the thesis: a fixed preprocessing
    backbone (features) plus a lightweight trainable linear head that can later
    be re-fit per user (adaptation).
    """

    def __init__(self, model: Pipeline | None = None) -> None:
        self._model = model or Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(
                        max_iter=1000,
                        class_weight="balanced",
                    ),
                ),
            ]
        )
        self._is_fitted = model is not None

    @property
    def is_fitted(self) -> bool:
        return self._is_fitted

    def fit(
        self,
        features: NDArray[np.floating[Any]],
        labels: NDArray[Any],
    ) -> SklearnIntentClassifier:
        """Fit the linear head on a labeled feature matrix."""

        if features.ndim != 2:
            raise ValueError("features must be shaped (n_samples, n_features)")
        if features.shape[0] != len(labels):
            raise ValueError("features and labels length mismatch")
        self._model.fit(features, labels)
        self._is_fitted = True
        return self

    def predict(self, features: FeatureVector) -> ClassifiedIntent:
        """Classify one online feature vector."""

        if not self._is_fitted:
            raise RuntimeError("SklearnIntentClassifier must be fitted before predict()")
        if not features.is_clean:
            return ClassifiedIntent(
                label=IntentLabel.IDLE,
                confidence=0.0,
                timestamp_s=features.timestamp_s,
                raw_scores={"artifact_rejected": 1.0},
            )

        x = features.values.reshape(1, -1)
        label = str(self._model.predict(x)[0])
        proba_map: dict[str, float] = {}
        confidence = 0.5
        if hasattr(self._model, "predict_proba"):
            probabilities = self._model.predict_proba(x)[0]
            classes = [str(c) for c in self._model.classes_]
            proba_map = {cls: float(p) for cls, p in zip(classes, probabilities, strict=True)}
            confidence = float(max(probabilities))

        return ClassifiedIntent(
            label=IntentLabel(label),
            confidence=confidence,
            timestamp_s=features.timestamp_s,
            raw_scores=proba_map,
        )

    def save(self, path: Path | str) -> None:
        """Persist the fitted pipeline to disk."""

        if not self._is_fitted:
            raise RuntimeError("Cannot save an unfitted classifier")
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self._model, destination)

    @classmethod
    def load(cls, path: Path | str) -> SklearnIntentClassifier:
        """Load a previously saved pipeline."""

        model = joblib.load(Path(path))
        return cls(model=model)
