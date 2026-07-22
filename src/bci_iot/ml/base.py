"""Shared classifier protocol for heuristic and trained models."""

from __future__ import annotations

from typing import Protocol

from bci_iot.types import ClassifiedIntent, FeatureVector


class IntentClassifier(Protocol):
    """Anything that maps a :class:`FeatureVector` to a :class:`ClassifiedIntent`."""

    def predict(self, features: FeatureVector) -> ClassifiedIntent:
        """Classify one feature vector."""
