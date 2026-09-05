"""Run one literature-prior impulse through the real software pipeline."""

from __future__ import annotations

from typing import Any

from bci_iot.acquisition.priors import COMMAND_PRIORS, synthesize_prior_window
from bci_iot.integrations.dispatcher import ActionDispatcher
from bci_iot.integrations.fake import FakeIntegrationClient
from bci_iot.integrations.router_control import RouterControlClient
from bci_iot.ml.prior_model import train_prior_impulse_classifier
from bci_iot.ml.sklearn_classifier import SklearnIntentClassifier
from bci_iot.preprocessing.features import BandPowerExtractor
from bci_iot.router.fsm import IntentRouter
from bci_iot.types import ActionContext, IntentLabel


class ImpulseDemoEngine:
    """Button → literature EEG window → features → ML → router → action."""

    def __init__(
        self,
        *,
        context: ActionContext = ActionContext.LIGHT_MODE,
        seed: int = 0,
        classifier: SklearnIntentClassifier | None = None,
    ) -> None:
        self.extractor = BandPowerExtractor(notch_hz=None)
        self.classifier = classifier or train_prior_impulse_classifier(seed=seed)
        self.router = IntentRouter(
            debounce_windows=1,
            confidence_threshold=0.35,
            initial_context=context,
            dry_run=True,
            action_map={
                "FOCUS": "home_assistant.turn_on",
                "RELAX": "home_assistant.turn_off",
                "ACCEPT": "phone.accept_call",
                "REJECT": "phone.reject_call",
            },
        )
        fake = FakeIntegrationClient()
        self.dispatcher = ActionDispatcher(
            {
                "spotify": fake,
                "home_assistant": fake,
                "phone": fake,
                "router": RouterControlClient(self.router),
            }
        )
        self.fake = fake
        self._seed = seed

    def set_context(self, context: ActionContext) -> None:
        self.router.set_context(context)

    def fire(self, command: str) -> dict[str, Any]:
        """Synthesize one prior window and run the full chain once."""

        key = command.strip().upper()
        if key not in COMMAND_PRIORS:
            raise KeyError(key)

        prior = COMMAND_PRIORS[key]
        window = synthesize_prior_window(key, seed=self._seed)
        self._seed += 1

        features = self.extractor.transform(window)
        intent = self.classifier.predict(features)

        if intent.label in {IntentLabel.ACCEPT, IntentLabel.REJECT}:
            self.router.set_context(ActionContext.CALL_MODE)
        elif intent.label in {IntentLabel.FOCUS, IntentLabel.RELAX}:
            if self.router.context in {ActionContext.IDLE, ActionContext.CALL_MODE}:
                self.router.set_context(ActionContext.LIGHT_MODE)

        action = self.router.route(intent)
        dispatch_result: dict[str, str] | None = None
        if action is not None:
            dispatch_result = self.dispatcher.dispatch(action)

        return {
            "command": key,
            "expected_intent": prior.intent.value,
            "prior_source": prior.source_note,
            "features": {
                "names": list(features.names),
                "values": [float(v) for v in features.values],
                "is_clean": features.is_clean,
            },
            "classified_intent": intent.label.value,
            "confidence": round(float(intent.confidence), 3),
            "match_expected": intent.label == prior.intent,
            "context": self.router.context.value,
            "action": None
            if action is None
            else {
                "name": action.name,
                "target": action.target,
                "payload": action.payload,
                "dry_run": action.dry_run,
            },
            "dispatch": dispatch_result,
            "actions_fired_total": len(self.fake.history),
        }
