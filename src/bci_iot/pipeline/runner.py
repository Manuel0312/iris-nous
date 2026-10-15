"""Wire acquisition → features → classifier → router → dispatcher."""

from __future__ import annotations

import time
from dataclasses import dataclass

from bci_iot.acquisition.base import EEGSource
from bci_iot.integrations.dispatcher import ActionDispatcher
from bci_iot.ml.base import IntentClassifier
from bci_iot.preprocessing.features import BandPowerExtractor
from bci_iot.router.fsm import IntentRouter
from bci_iot.types import ActionCommand, ClassifiedIntent


@dataclass(slots=True)
class PipelineStepResult:
    intent: ClassifiedIntent
    action: ActionCommand | None
    is_clean: bool = True
    latency_ms: float = 0.0
    stage_ms: dict[str, float] | None = None


class PipelineRunner:
    """Run a finite number of windows through the full software chain."""

    def __init__(
        self,
        source: EEGSource,
        extractor: BandPowerExtractor,
        classifier: IntentClassifier,
        router: IntentRouter,
        dispatcher: ActionDispatcher | None = None,
    ) -> None:
        self.source = source
        self.extractor = extractor
        self.classifier = classifier
        self.router = router
        self.dispatcher = dispatcher

    def run(self, max_windows: int) -> list[PipelineStepResult]:
        """Process up to ``max_windows`` EEG windows and return step results."""

        if max_windows < 1:
            raise ValueError("max_windows must be >= 1")

        results: list[PipelineStepResult] = []
        with self.source:
            for index, window in enumerate(self.source.iter_windows()):
                if index >= max_windows:
                    break
                t0 = time.perf_counter()
                t_feat0 = t0
                features = self.extractor.transform(window)
                t_feat1 = time.perf_counter()
                intent = self.classifier.predict(features)
                t_ml = time.perf_counter()
                action = None
                if features.is_clean:
                    action = self.router.route(intent)
                    t_route = time.perf_counter()
                    if action is not None and self.dispatcher is not None:
                        self.dispatcher.dispatch(action)
                    t_end = time.perf_counter()
                else:
                    t_route = t_ml
                    t_end = t_ml
                stage = {
                    "features_ms": round((t_feat1 - t_feat0) * 1000, 2),
                    "ml_ms": round((t_ml - t_feat1) * 1000, 2),
                    "route_ms": round((t_route - t_ml) * 1000, 2),
                    "dispatch_ms": round((t_end - t_route) * 1000, 2),
                }
                results.append(
                    PipelineStepResult(
                        intent=intent,
                        action=action,
                        is_clean=features.is_clean,
                        latency_ms=round((t_end - t0) * 1000, 2),
                        stage_ms=stage,
                    )
                )
        return results
