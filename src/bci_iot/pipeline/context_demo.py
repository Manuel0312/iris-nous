"""Context-aware demo: direct intent + short Alexa-like disambiguation + channel gates."""

from __future__ import annotations

from typing import Any, Literal

from bci_iot.acquisition.priors import COMMAND_PRIORS, synthesize_prior_window
from bci_iot.ml.prior_model import train_prior_impulse_classifier
from bci_iot.ml.sklearn_classifier import SklearnIntentClassifier
from bci_iot.preprocessing.features import BandPowerExtractor
from bci_iot.router.channels import ChannelGate, ChannelId, WorldState
from bci_iot.types import IntentLabel

Phase = Literal["idle", "confirm"]

# Button / impulse → prior EEG template
CONTROL_TO_PRIOR = {
    "ACCENDI": "ACCENDI",
    "SPEGNI": "SPEGNI",
    "APRI": "RISPONDI",  # “open / accept” spectral prior
    "SI": "RISPONDI",
    "NO": "RIFIUTA",
    "NEXT": "ACCENDI",
}


class ContextDemoEngine:
    """User thinks an action → system proposes the right target → SÌ/NO → closes.

    Channels (call, messages, music, home) open/close from world events so the
    classifier path does not compete with impossible actions.
    """

    def __init__(
        self,
        *,
        seed: int = 0,
        classifier: SklearnIntentClassifier | None = None,
    ) -> None:
        self.gate = ChannelGate(WorldState())
        self.extractor = BandPowerExtractor(notch_hz=None)
        self.classifier = classifier or train_prior_impulse_classifier(seed=seed)
        self.phase: Phase = "idle"
        self.pending_action: str | None = None  # turn_on | turn_off | open_app | answer | reject | music_next
        self.candidates: list[str] = []
        self.candidate_index = 0
        self.prompt: str | None = None
        self.last_effect: str | None = None
        self.opened_app: str | None = None
        self.phone: Literal["idle", "accept", "reject"] = "idle"
        self.track_number = 1
        self._seed = seed

    # --- world events (simulate notifications / call / music) ---

    def event_message(self, *, app: str = "WhatsApp", sender: str = "Marco") -> dict[str, Any]:
        self.gate.world.unread_message = True
        self.gate.world.message_app = app
        self.gate.world.message_from = sender
        self._reset_confirm()
        return self.status(
            message=(
                f"Messaggio da {sender} su {app}. "
                "Canale MESSAGES aperto (effimero: si chiude dopo apri/ignora)."
            )
        )

    def event_call(self, *, caller: str = "Anna") -> dict[str, Any]:
        self.gate.world.incoming_call = True
        self.gate.world.caller_name = caller
        self._reset_confirm()
        return self.status(
            message=(
                f"Chiamata da {caller}. "
                "Canale CALL aperto solo ora (si chiude dopo rispondi/rifiuta)."
            )
        )

    def event_music(self, playing: bool = True) -> dict[str, Any]:
        self.gate.world.music_playing = playing
        self._reset_confirm()
        if playing:
            return self.status(
                message="Musica in play. Canale MUSIC sticky (resta aperto finché streami)."
            )
        return self.status(message="Musica ferma. Canale MUSIC chiuso.")

    def event_clear(self) -> dict[str, Any]:
        w = self.gate.world
        w.unread_message = False
        w.message_app = ""
        w.message_from = ""
        w.incoming_call = False
        w.caller_name = ""
        w.music_playing = False
        self.opened_app = None
        self.phone = "idle"
        self._reset_confirm()
        return self.status(message="Eventi azzerati. Resta il canale HOME.")

    # --- impulses ---

    def fire(self, command: str) -> dict[str, Any]:
        key = command.strip().upper().replace("Ì", "I")
        aliases = {"SÌ": "SI", "YES": "SI", "OPEN": "APRI"}
        key = aliases.get(key, key)
        if key not in CONTROL_TO_PRIOR:
            raise KeyError(key)

        prior_key = CONTROL_TO_PRIOR[key]
        _ = COMMAND_PRIORS[prior_key]
        window = synthesize_prior_window(prior_key, seed=self._seed)
        self._seed += 1
        features = self.extractor.transform(window)
        intent = self.classifier.predict(features)

        expected_map = {
            "ACCENDI": IntentLabel.FOCUS,
            "SPEGNI": IntentLabel.RELAX,
            "APRI": IntentLabel.ACCEPT,
            "NEXT": IntentLabel.FOCUS,
            "SI": IntentLabel.ACCEPT,
            "NO": IntentLabel.REJECT,
        }
        expected = expected_map[key]
        msg = ""
        effect: str | None = None

        if self.phase == "confirm":
            msg, effect = self._handle_confirm(key)
        else:
            msg, effect = self._handle_idle_intent(key)

        payload = self.status(message=msg)
        payload.update(
            {
                "command": key,
                "classified_intent": intent.label.value,
                "expected_intent": expected.value,
                "confidence": round(float(intent.confidence), 3),
                "match_expected": intent.label == expected,
                "effect": effect,
                "features": {
                    "names": list(features.names),
                    "values": [float(v) for v in features.values],
                    "is_clean": features.is_clean,
                },
            }
        )
        return payload

    def status(self, message: str = "") -> dict[str, Any]:
        gate = self.gate.status()
        return {
            **gate,
            "phase": self.phase,
            "prompt": self.prompt,
            "pending_action": self.pending_action,
            "candidate": self.candidates[self.candidate_index] if self.candidates else None,
            "message": message,
            "opened_app": self.opened_app,
            "phone": self.phone,
            "track_number": self.track_number,
            "bulb_on": any(self.gate.world.device_on.values()),
            "last_effect": self.last_effect,
            "hint": self._hint(),
        }

    def _hint(self) -> str:
        if self.phase == "confirm":
            return "Alexa/app in ascolto: rispondi SÌ o NO (poi il canale effimero si chiude)."
        opened = self.gate.open_channels()
        parts: list[str] = []
        for ch in (ChannelId.HOME, ChannelId.MUSIC, ChannelId.CALL, ChannelId.MESSAGES):
            if ch in opened:
                kind = "sticky" if ch == ChannelId.MUSIC else (
                    "sempre" if ch == ChannelId.HOME else "effimero"
                )
                parts.append(f"{ch.value}({kind})")
        return "Canali: " + ", ".join(parts) + ". Pensa/premi un’azione."

    def _reset_confirm(self) -> None:
        self.phase = "idle"
        self.pending_action = None
        self.candidates = []
        self.candidate_index = 0
        self.prompt = None

    def _cancel_confirm(self) -> str:
        """Close Alexa prompt and tear down any ephemeral channel involved."""

        action = self.pending_action
        self._reset_confirm()
        if action in {"answer_call", "reject_call"}:
            self.gate.close_call()
            return "Chiamata ignorata. Canale CALL chiuso. Alexa chiusa."
        if action == "open_app":
            self.gate.close_messages()
            return "Messaggio ignorato. Canale MESSAGES chiuso. Alexa chiusa."
        return "Ok, annullo. Alexa chiusa."

    def _close_after_action(self, message: str, effect: str) -> tuple[str, str]:
        self.last_effect = effect
        self._reset_confirm()
        return message + " Alexa chiusa.", effect

    def _start_confirm(self, action: str, candidates: list[str], prompt: str) -> tuple[str, None]:
        self.phase = "confirm"
        self.pending_action = action
        self.candidates = candidates
        self.candidate_index = 0
        self.prompt = prompt
        return prompt, None

    def _handle_idle_intent(self, key: str) -> tuple[str, str | None]:
        opened = self.gate.open_channels()
        world = self.gate.world

        # Priority: CALL overrides almost everything for answer/reject/open semantics
        if ChannelId.CALL in opened and key in {"APRI", "SI", "ACCENDI"}:
            prompt = f"Alexa: rispondere a {world.caller_name or 'chiamata'}?"
            return self._start_confirm("answer_call", ["call"], prompt)
        if ChannelId.CALL in opened and key in {"SPEGNI", "NO"}:
            prompt = f"Alexa: rifiutare la chiamata di {world.caller_name or 'sconosciuto'}?"
            return self._start_confirm("reject_call", ["call"], prompt)

        if key == "APRI":
            if ChannelId.MESSAGES in opened:
                app = world.message_app or "Messaggi"
                who = world.message_from or "nuovo messaggio"
                prompt = f"Alexa: aprire {app} (da {who})?"
                return self._start_confirm("open_app", [app], prompt)
            return "Canale MESSAGES chiuso (nessun messaggio). Niente da aprire.", None

        if key == "NEXT":
            if ChannelId.MUSIC in opened:
                prompt = "Alexa: passare alla prossima canzone?"
                return self._start_confirm("music_next", ["spotify"], prompt)
            return "Canale MUSIC chiuso. Metti prima la musica in play (evento).", None

        if key == "ACCENDI":
            if ChannelId.HOME not in opened:
                return "Canale HOME chiuso.", None
            offs = [d for d in world.home_devices if not world.device_on.get(d, False)]
            if not offs:
                return "Tutti i device sono già accesi.", None
            if len(offs) == 1:
                # No ambiguity → direct action, no question
                return self._apply("turn_on", offs[0])
            prompt = f"Alexa: vuoi accendere {offs[0]}?"
            return self._start_confirm("turn_on", offs, prompt)

        if key == "SPEGNI":
            ons = [d for d in world.home_devices if world.device_on.get(d, False)]
            if not ons:
                return "Nessun device acceso da spegnere.", None
            if len(ons) == 1:
                return self._apply("turn_off", ons[0])
            prompt = f"Alexa: vuoi spegnere {ons[0]}?"
            return self._start_confirm("turn_off", ons, prompt)

        if key in {"SI", "NO"}:
            return "Nessuna proposta aperta. Pensa prima ACCENDI / APRI / NEXT…", None

        return f"Comando {key} non gestito in idle.", None

    def _handle_confirm(self, key: str) -> tuple[str, str | None]:
        if key == "SI":
            target = self.candidates[self.candidate_index]
            action = self.pending_action or ""
            return self._apply(action, target)
        if key == "NO":
            self.candidate_index += 1
            if self.candidate_index >= len(self.candidates):
                return self._cancel_confirm(), None
            nxt = self.candidates[self.candidate_index]
            if self.pending_action == "turn_on":
                self.prompt = f"Alexa: allora {nxt}?"
            elif self.pending_action == "turn_off":
                self.prompt = f"Alexa: allora spegnere {nxt}?"
            else:
                self.prompt = f"Alexa: allora {nxt}?"
            return self.prompt, None
        # New intent while confirming → cancel ephemeral if needed, then reinterpret
        cancel_msg = self._cancel_confirm()
        msg, effect = self._handle_idle_intent(key)
        return f"{cancel_msg} {msg}", effect

    def _apply(self, action: str, target: str) -> tuple[str, str]:
        world = self.gate.world
        if action == "turn_on":
            world.device_on[target] = True
            return self._close_after_action(f"Acceso: {target}.", f"on:{target}")
        if action == "turn_off":
            world.device_on[target] = False
            return self._close_after_action(f"Spento: {target}.", f"off:{target}")
        if action == "open_app":
            self.opened_app = target
            self.gate.close_messages()
            return self._close_after_action(
                f"Apro {target}. Canale MESSAGES chiuso.",
                f"app:{target}",
            )
        if action == "answer_call":
            self.phone = "accept"
            self.gate.close_call()
            return self._close_after_action(
                "Chiamata accettata. Canale CALL chiuso.",
                "call:accept",
            )
        if action == "reject_call":
            self.phone = "reject"
            self.gate.close_call()
            return self._close_after_action(
                "Chiamata rifiutata. Canale CALL chiuso.",
                "call:reject",
            )
        if action == "music_next":
            self.track_number += 1
            # MUSIC stays open while streaming (sticky)
            return self._close_after_action(
                f"Prossima canzone (traccia {self.track_number}). Canale MUSIC resta aperto.",
                "music_next",
            )
        self._reset_confirm()
        return f"Azione sconosciuta: {action}", "none"


def list_context_commands() -> list[dict[str, str]]:
    return [
        {"command": "ACCENDI", "label": "ACCENDI", "description": "Accendi un device (casa)"},
        {"command": "SPEGNI", "label": "SPEGNI", "description": "Spegni un device"},
        {"command": "APRI", "label": "APRI", "description": "Apri messaggio / rispondi se chiama"},
        {"command": "NEXT", "label": "NEXT", "description": "Prossima canzone (se musica attiva)"},
        {"command": "SI", "label": "SÌ", "description": "Conferma proposta Alexa"},
        {"command": "NO", "label": "NO", "description": "Proposta successiva / annulla"},
    ]
