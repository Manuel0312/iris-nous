"""Tests for heuristic classifier and intent router FSM."""

from __future__ import annotations

import numpy as np

from bci_iot.ml import HeuristicIntentClassifier
from bci_iot.router import IntentRouter
from bci_iot.types import ActionContext, ClassifiedIntent, FeatureVector, IntentLabel


def _features(ratio: float) -> FeatureVector:
    return FeatureVector(
        values=np.array([0.0, 0.0, ratio], dtype=np.float64),
        names=("alpha_logpower", "beta_logpower", "alpha_beta_ratio"),
        timestamp_s=0.0,
    )


def test_heuristic_classifier_focus_and_relax() -> None:
    clf = HeuristicIntentClassifier(ratio_threshold=1.0, margin=0.1)
    assert clf.predict(_features(0.5)).label == IntentLabel.FOCUS
    assert clf.predict(_features(1.5)).label == IntentLabel.RELAX
    assert clf.predict(_features(1.0)).label == IntentLabel.IDLE


def test_router_debounce_emits_spotify_next() -> None:
    router = IntentRouter(debounce_windows=3, confidence_threshold=0.5)
    router.set_context(ActionContext.MUSIC_MODE)

    intent = ClassifiedIntent(label=IntentLabel.FOCUS, confidence=0.9, timestamp_s=0.0)
    assert router.route(intent) is None
    assert router.route(intent) is None
    action = router.route(intent)
    assert action is not None
    assert action.name == "spotify.next_track"
