"""MENU + SÌ/NO dialogue: user opens the menu, software asks briefly, then goes quiet."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from bci_iot.acquisition.priors import COMMAND_PRIORS, synthesize_prior_window
from bci_iot.ml.prior_model import train_prior_impulse_classifier
from bci_iot.ml.sklearn_classifier import SklearnIntentClassifier
from bci_iot.preprocessing.features import BandPowerExtractor
from bci_iot.types import IntentLabel

DialoguePhase = Literal["idle", "menu"]


@dataclass(frozen=True, slots=True)
class Question:
    """One yes/no gate offered after the user opens MENU."""

    question_id: str
    text: str
    effect: str


DEFAULT_QUESTIONS: tuple[Question, ...] = (
    Question("music_next", "Vuoi cambiare canzone?", "music_next"),
    Question("light_on", "Vuoi accendere la luce?", "light_on"),
    Question("light_off", "Vuoi spegnere la luce?", "light_off"),
    Question("call_accept", "Vuoi rispondere alla chiamata?", "call_accept"),
    Question("call_reject", "Vuoi rifiutare la chiamata?", "call_reject"),
)

# Map dialogue buttons → spectral prior keys already in COMMAND_PRIORS.
DIALOGUE_TO_PRIOR = {
    "MENU": "ACCENDI",  # attention / “voglio fare qualcosa”
    "SI": "RISPONDI",
    "NO": "RIFIUTA",
}


class DialogueDemoEngine:
    """User-initiated menu + short yes/no questions (no continuous polling)."""

    def __init__(
        self,
        *,
        questions: tuple[Question, ...] = DEFAULT_QUESTIONS,
        seed: int = 0,
        classifier: SklearnIntentClassifier | None = None,
    ) -> None:
        self.questions = questions
        self.extractor = BandPowerExtractor(notch_hz=None)
        self.classifier = classifier or train_prior_impulse_classifier(seed=seed)
        self.phase: DialoguePhase = "idle"
        self.question_index = 0
        self.bulb_on = False
        self.phone: Literal["idle", "accept", "reject"] = "idle"
        self.track_number = 1
        self.last_effect: str | None = None
        self._seed = seed

    def status(self) -> dict[str, Any]:
        current = None
        if self.phase == "menu" and self.question_index < len(self.questions):
            q = self.questions[self.question_index]
            current = {"id": q.question_id, "text": q.text}
        return {
            "phase": self.phase,
            "question": current,
            "question_index": self.question_index,
            "questions_total": len(self.questions),
            "bulb_on": self.bulb_on,
            "phone": self.phone,
            "track_number": self.track_number,
            "last_effect": self.last_effect,
            "hint": (
                "Premi MENU quando vuoi fare qualcosa."
                if self.phase == "idle"
                else "Rispondi SÌ oppure NO alla domanda."
            ),
        }

    def fire(self, command: str) -> dict[str, Any]:
        """Run EEG prior → classify → advance dialogue → optional effect."""

        key = command.strip().upper()
        aliases = {"SÌ": "SI", "YES": "SI", "NOPE": "NO"}
        key = aliases.get(key, key)
        if key not in DIALOGUE_TO_PRIOR:
            raise KeyError(key)

        prior_key = DIALOGUE_TO_PRIOR[key]
        prior = COMMAND_PRIORS[prior_key]
        window = synthesize_prior_window(prior_key, seed=self._seed)
        self._seed += 1
        features = self.extractor.transform(window)
        intent = self.classifier.predict(features)

        # Prefer the button's expected intent for stable demo UX when ML is close;
        # still expose classifier output for transparency.
        expected = {
            "MENU": IntentLabel.FOCUS,
            "SI": IntentLabel.ACCEPT,
            "NO": IntentLabel.REJECT,
        }[key]
        control = key

        message = ""
        effect: str | None = None

        if self.phase == "idle":
            if control == "MENU":
                self.phase = "menu"
                self.question_index = 0
                self.last_effect = None
                message = "Menu aperto. Ti faccio poche domande."
            elif control in {"SI", "NO"}:
                message = "Nessun menu aperto. Premi prima MENU (quando vuoi tu)."
        else:
            if control == "MENU":
                message = "Menu già aperto. Rispondi SÌ o NO."
            elif control == "SI":
                effect = self.questions[self.question_index].effect
                self._apply_effect(effect)
                self.last_effect = effect
                self.phase = "idle"
                self.question_index = 0
                message = f"Ok: eseguito «{effect}». Torno in silenzio."
            elif control == "NO":
                self.question_index += 1
                if self.question_index >= len(self.questions):
                    self.phase = "idle"
                    self.question_index = 0
                    message = "Fine domande. Torno in silenzio (nessuna azione)."
                else:
                    message = "Ok, passo alla domanda successiva."

        payload = self.status()
        payload.update(
            {
                "command": key,
                "prior_key": prior_key,
                "expected_intent": expected.value,
                "classified_intent": intent.label.value,
                "confidence": round(float(intent.confidence), 3),
                "match_expected": intent.label == expected
                or (key == "MENU" and intent.label == IntentLabel.FOCUS),
                "message": message,
                "effect": effect,
                "features": {
                    "names": list(features.names),
                    "values": [float(v) for v in features.values],
                    "is_clean": features.is_clean,
                },
            }
        )
        return payload

    def _apply_effect(self, effect: str) -> None:
        if effect == "music_next":
            self.track_number += 1
            self.phone = "idle"
        elif effect == "light_on":
            self.bulb_on = True
            self.phone = "idle"
        elif effect == "light_off":
            self.bulb_on = False
            self.phone = "idle"
        elif effect == "call_accept":
            self.phone = "accept"
        elif effect == "call_reject":
            self.phone = "reject"


def list_dialogue_commands() -> list[dict[str, str]]:
    return [
        {
            "command": "MENU",
            "label": "MENU",
            "description": "Apri il menu (lo pensi tu quando vuoi fare qualcosa).",
        },
        {
            "command": "SI",
            "label": "SÌ",
            "description": "Conferma la domanda attuale.",
        },
        {
            "command": "NO",
            "label": "NO",
            "description": "Salta / rifiuta e passa avanti.",
        },
    ]
