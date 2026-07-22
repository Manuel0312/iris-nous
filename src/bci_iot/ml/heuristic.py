"""Simple rule-based classifier used as a pipeline placeholder before trained ML."""

from __future__ import annotations

from bci_iot.types import ClassifiedIntent, FeatureVector, IntentLabel


class HeuristicIntentClassifier:
    """Map Alpha/Beta ratio to RELAX vs FOCUS (dev scaffold, not production ML).

    Higher alpha/beta ratio → RELAX; lower → FOCUS. Values near the threshold
    yield IDLE with reduced confidence. Replace with a trained model in sector D.
    """

    def __init__(self, *, ratio_threshold: float = 1.0, margin: float = 0.15) -> None:
        if margin < 0:
            raise ValueError("margin must be non-negative")
        self.ratio_threshold = ratio_threshold
        self.margin = margin

    def predict(self, features: FeatureVector) -> ClassifiedIntent:
        """Classify one feature vector into an :class:`IntentLabel`."""

        if not features.is_clean:
            return ClassifiedIntent(
                label=IntentLabel.IDLE,
                confidence=0.0,
                timestamp_s=features.timestamp_s,
                raw_scores={"artifact_rejected": 1.0},
            )

        names = {name: idx for idx, name in enumerate(features.names)}
        if "alpha_beta_ratio" not in names:
            raise KeyError("FeatureVector must include 'alpha_beta_ratio'")

        ratio = float(features.values[names["alpha_beta_ratio"]])
        if ratio >= self.ratio_threshold + self.margin:
            label = IntentLabel.RELAX
            confidence = min(1.0, 0.55 + (ratio - self.ratio_threshold) * 0.1)
        elif ratio <= self.ratio_threshold - self.margin:
            label = IntentLabel.FOCUS
            confidence = min(1.0, 0.55 + (self.ratio_threshold - ratio) * 0.1)
        else:
            label = IntentLabel.IDLE
            confidence = 0.5

        return ClassifiedIntent(
            label=label,
            confidence=float(confidence),
            timestamp_s=features.timestamp_s,
            raw_scores={"alpha_beta_ratio": ratio},
        )
