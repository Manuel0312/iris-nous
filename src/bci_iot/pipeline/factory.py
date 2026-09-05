"""Assemble a runnable pipeline from config, optional user profile, and model."""

from __future__ import annotations

from pathlib import Path

from bci_iot.accounts.store import ProfileStore
from bci_iot.acquisition.factory import create_eeg_source
from bci_iot.config import AppConfig, load_app_config
from bci_iot.integrations.factory import build_dispatcher
from bci_iot.ml.heuristic import HeuristicIntentClassifier
from bci_iot.ml.sklearn_classifier import SklearnIntentClassifier
from bci_iot.pipeline.runner import PipelineRunner
from bci_iot.preprocessing.features import BandPowerExtractor
from bci_iot.router.fsm import IntentRouter
from bci_iot.types import ActionContext


def build_pipeline(
    config: AppConfig | None = None,
    *,
    username: str | None = None,
    max_windows_cap: int | None = None,
    prefer_sklearn: bool = True,
    model_path: Path | str | None = None,
) -> PipelineRunner:
    """Build acquisition → features → ML → router → integrations.

    Args:
        config: Loaded app config (default YAML if omitted).
        username: Optional profile whose ``action_map`` drives the router.
        max_windows_cap: Limit synthetic source length (useful for CLI demos).
        prefer_sklearn: Load sklearn model if the file exists, else heuristic.
        model_path: Override ``config.ml.model_path``.
    """

    cfg = config or load_app_config()
    action_map: dict[str, str] = {}
    if username:
        store = ProfileStore(cfg.accounts.data_dir)
        profile = store.get(username)
        if profile is None:
            raise KeyError(f"Unknown profile username={username!r}")
        action_map = dict(profile.action_map)

    source = create_eeg_source(cfg.acquisition, max_windows=max_windows_cap, seed=42)
    extractor = BandPowerExtractor(
        bandpass_hz=cfg.preprocessing.bandpass_hz,
        notch_hz=cfg.preprocessing.notch_hz,
        alpha_band_hz=cfg.preprocessing.alpha_band_hz,
        beta_band_hz=cfg.preprocessing.beta_band_hz,
    )

    path = Path(model_path or cfg.ml.model_path)
    if prefer_sklearn and path.exists():
        classifier: HeuristicIntentClassifier | SklearnIntentClassifier = (
            SklearnIntentClassifier.load(path)
        )
    else:
        classifier = HeuristicIntentClassifier()

    try:
        initial = ActionContext(cfg.router.default_context)
    except ValueError:
        initial = ActionContext.IDLE

    router = IntentRouter(
        debounce_windows=cfg.router.debounce_windows,
        confidence_threshold=cfg.ml.confidence_threshold,
        initial_context=initial,
        action_map=action_map,
        dry_run=cfg.integrations.dry_run,
    )
    dispatcher = build_dispatcher(cfg, router)
    return PipelineRunner(
        source=source,
        extractor=extractor,
        classifier=classifier,
        router=router,
        dispatcher=dispatcher,
    )
