"""End-to-end smoke test for the pipeline runner."""

from __future__ import annotations

from bci_iot.acquisition import SyntheticEEGSource
from bci_iot.integrations import ActionDispatcher, FakeIntegrationClient
from bci_iot.ml import HeuristicIntentClassifier
from bci_iot.pipeline import PipelineRunner
from bci_iot.preprocessing import BandPowerExtractor
from bci_iot.router import IntentRouter
from bci_iot.types import ActionContext


def test_pipeline_runs_without_network() -> None:
    source = SyntheticEEGSource(max_windows=5, window_seconds=0.5, seed=7)
    fake = FakeIntegrationClient()
    dispatcher = ActionDispatcher({"spotify": fake, "home_assistant": fake, "router": fake})
    router = IntentRouter(debounce_windows=2, confidence_threshold=0.0)
    router.set_context(ActionContext.MUSIC_MODE)

    runner = PipelineRunner(
        source=source,
        extractor=BandPowerExtractor(notch_hz=None),
        classifier=HeuristicIntentClassifier(),
        router=router,
        dispatcher=dispatcher,
    )
    results = runner.run(max_windows=5)
    assert len(results) == 5
    assert all(r.intent is not None for r in results)
