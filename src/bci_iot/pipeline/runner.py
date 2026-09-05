"""Wire acquisition → features → classifier → router → dispatcher."""

from __future__ import annotations

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
                features = self.extractor.transform(window)
                intent = self.classifier.predict(features)
                action = None
                if features.is_clean:
                    action = self.router.route(intent)
                    if action is not None and self.dispatcher is not None:
                        self.dispatcher.dispatch(action)
                results.append(
                    PipelineStepResult(
                        intent=intent,
                        action=action,
                        is_clean=features.is_clean,
                    )
                )
        return results
