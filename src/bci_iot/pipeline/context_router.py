"""Context exclusion router: headset only says SÌ/NO; the site picks the target.

Product rule: call > message > music > idle. Only the highest active context
receives the binary decision. Ephemeral contexts (call, message) close after
a decision; music stays sticky while playback is on.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

ContextKind = Literal["idle", "call", "message", "music"]
YesNo = Literal["SI", "NO"]
IntentAction = Literal[
    "noop",
    "answer_call",
    "reject_call",
    "open_message",
    "dismiss_message",
    "next_track",
    "keep_track",
]

# Highest active context wins.
CONTEXT_PRIORITY: dict[ContextKind, int] = {
    "call": 100,
    "message": 80,
    "music": 40,
    "idle": 0,
}

# (focus, SI/NO) → action the site executes.
DECISION_MATRIX: dict[tuple[ContextKind, YesNo], IntentAction] = {
    ("call", "SI"): "answer_call",
    ("call", "NO"): "reject_call",
    ("message", "SI"): "open_message",
    ("message", "NO"): "dismiss_message",
    ("music", "SI"): "next_track",
    ("music", "NO"): "keep_track",
    ("idle", "SI"): "noop",
    ("idle", "NO"): "noop",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_yes_no(raw: str) -> YesNo | None:
    """Map headset / UI labels to SI or NO. Returns None if not binary."""

    key = (raw or "").strip().upper().replace("Ì", "I")
    if key in {"SI", "YES", "RISPONDI", "ACCEPT", "APRI"}:
        return "SI"
    if key in {"NO", "RIFIUTA", "REJECT"}:
        return "NO"
    return None


def resolve_focus(
    *,
    incoming_call: bool,
    unread_message: bool,
    music_playing: bool,
) -> ContextKind:
    """Pick the single active focus by priority."""

    if incoming_call:
        return "call"
    if unread_message:
        return "message"
    if music_playing:
        return "music"
    return "idle"


def map_decision(focus: ContextKind, answer: YesNo) -> IntentAction:
    return DECISION_MATRIX[(focus, answer)]


@dataclass
class FocusSnapshot:
    """What the UI should show as the active decision target."""

    kind: ContextKind
    title: str
    detail: str
    prompt: str  # e.g. «Sto decidendo su: … — pensa SÌ o NO»
    yes_label: str
    no_label: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DecisionRecord:
    at: str
    answer: YesNo
    focus: ContextKind
    action: IntentAction
    focus_title: str
    feedback: str
    via: str = "context_router"
    impulse_kind: str = ""
    execution: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ContextWorld:
    """Simulated / live world flags for one user session."""

    incoming_call: bool = False
    caller_name: str = ""
    unread_message: bool = False
    message_from: str = ""
    message_app: str = ""
    music_playing: bool = False
    track_hint: str = ""


class ContextRouter:
    """Per-user live context: simulate events, resolve focus, map SÌ/NO → action."""

    def __init__(self, *, username: str = "") -> None:
        self.username = username
        self.world = ContextWorld()
        self.live_mode = False
        self.last_decision: DecisionRecord | None = None
        self.history: list[dict[str, Any]] = []

    # --- simulate / set events ---

    def simulate_call(self, *, caller: str = "Anna") -> dict[str, Any]:
        self.world.incoming_call = True
        self.world.caller_name = (caller or "Anna").strip() or "Anna"
        return self.status(message=f"Chiamata simulata da {self.world.caller_name}.")

    def simulate_message(
        self,
        *,
        sender: str = "Marco",
        app: str = "WhatsApp",
    ) -> dict[str, Any]:
        self.world.unread_message = True
        self.world.message_from = (sender or "Marco").strip() or "Marco"
        self.world.message_app = (app or "WhatsApp").strip() or "WhatsApp"
        return self.status(
            message=(
                f"Messaggio simulato da {self.world.message_from} "
                f"su {self.world.message_app}."
            )
        )

    def set_music(self, playing: bool = True, *, track: str = "") -> dict[str, Any]:
        self.world.music_playing = bool(playing)
        if playing:
            self.world.track_hint = (track or self.world.track_hint or "in riproduzione").strip()
            return self.status(message="Musica attiva (priorità sotto chiamata/messaggio).")
        self.world.track_hint = ""
        return self.status(message="Musica ferma.")

    def clear_events(self) -> dict[str, Any]:
        self.world = ContextWorld()
        return self.status(message="Contesti azzerati — focus idle.")

    def set_live_mode(self, enabled: bool) -> dict[str, Any]:
        self.live_mode = bool(enabled)
        msg = (
            "Modalità live: SÌ/NO dalla cuffia seguono il contesto attivo."
            if self.live_mode
            else "Modalità live spenta (calibrazione cuffia non passa dal router)."
        )
        return self.status(message=msg)

    # --- focus / decision ---

    def active_focus(self) -> ContextKind:
        return resolve_focus(
            incoming_call=self.world.incoming_call,
            unread_message=self.world.unread_message,
            music_playing=self.world.music_playing,
        )

    def focus_snapshot(self) -> FocusSnapshot:
        kind = self.active_focus()
        w = self.world
        if kind == "call":
            who = w.caller_name or "sconosciuto"
            title = f"Chiamata da {who}"
            return FocusSnapshot(
                kind=kind,
                title=title,
                detail="Priorità massima: la musica e i messaggi restano in attesa.",
                prompt=f"Sto decidendo su: {title} — pensa SÌ o NO",
                yes_label="Rispondi",
                no_label="Rifiuta",
            )
        if kind == "message":
            who = w.message_from or "nuovo messaggio"
            app = w.message_app or "Messaggi"
            title = f"Messaggio da {who} ({app})"
            return FocusSnapshot(
                kind=kind,
                title=title,
                detail="Apri o ignora; poi il canale messaggio si chiude.",
                prompt=f"Sto decidendo su: {title} — pensa SÌ o NO",
                yes_label="Apri",
                no_label="Ignora",
            )
        if kind == "music":
            hint = w.track_hint or "brano in play"
            title = f"Musica — {hint}"
            return FocusSnapshot(
                kind=kind,
                title=title,
                detail="SÌ = prossima canzone · NO = tieni questa.",
                prompt=f"Sto decidendo su: {title} — pensa SÌ o NO",
                yes_label="Cambia canzone",
                no_label="Tieni questa",
            )
        return FocusSnapshot(
            kind="idle",
            title="Nessun evento attivo",
            detail="Simula una chiamata, un messaggio o la musica per dare un focus al SÌ/NO.",
            prompt="Sto decidendo su: niente in questo momento — simula un evento, poi pensa SÌ o NO",
            yes_label="SÌ",
            no_label="NO",
        )

    def decide(
        self,
        answer: YesNo | str,
        *,
        impulse_kind: str = "",
        via: str = "context_router",
        execution: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Apply SÌ/NO to the current focus; close ephemeral contexts."""

        yn = answer if answer in ("SI", "NO") else normalize_yes_no(str(answer))
        if yn is None:
            raise ValueError("Serve SÌ o NO (o RISPONDI / RIFIUTA).")

        snap = self.focus_snapshot()
        action = map_decision(snap.kind, yn)
        feedback = self._apply_side_effects(action, snap)
        record = DecisionRecord(
            at=_utc_now(),
            answer=yn,
            focus=snap.kind,
            action=action,
            focus_title=snap.title,
            feedback=feedback,
            via=via,
            impulse_kind=(impulse_kind or yn).strip().upper(),
            execution=dict(execution or {}),
        )
        self.last_decision = record
        self.history.append(record.to_dict())
        self.history = self.history[-30:]
        payload = self.status(message=feedback)
        payload["decision"] = record.to_dict()
        return payload

    def _apply_side_effects(self, action: IntentAction, snap: FocusSnapshot) -> str:
        w = self.world
        if action == "answer_call":
            who = w.caller_name or "chiamata"
            w.incoming_call = False
            w.caller_name = ""
            return f"Chiamata di {who} accettata. Focus chiuso."
        if action == "reject_call":
            who = w.caller_name or "chiamata"
            w.incoming_call = False
            w.caller_name = ""
            return f"Chiamata di {who} rifiutata. Focus chiuso."
        if action == "open_message":
            who = w.message_from or "messaggio"
            app = w.message_app or "Messaggi"
            w.unread_message = False
            w.message_from = ""
            w.message_app = ""
            return f"Apro {app} (da {who}). Canale messaggio chiuso."
        if action == "dismiss_message":
            who = w.message_from or "messaggio"
            w.unread_message = False
            w.message_from = ""
            w.message_app = ""
            return f"Messaggio di {who} ignorato. Canale messaggio chiuso."
        if action == "next_track":
            return "Decisione: prossima canzone (musica resta attiva)."
        if action == "keep_track":
            return "Decisione: tieni questa canzone (nessun cambio)."
        return "Nessun evento attivo: SÌ/NO registrato senza azione."

    def status(self, message: str = "") -> dict[str, Any]:
        snap = self.focus_snapshot()
        active = {
            "call": self.world.incoming_call,
            "message": self.world.unread_message,
            "music": self.world.music_playing,
        }
        return {
            "username": self.username,
            "live_mode": self.live_mode,
            "focus": snap.to_dict(),
            "active_contexts": active,
            "priority_order": ["call", "message", "music", "idle"],
            "world": {
                "incoming_call": self.world.incoming_call,
                "caller_name": self.world.caller_name,
                "unread_message": self.world.unread_message,
                "message_from": self.world.message_from,
                "message_app": self.world.message_app,
                "music_playing": self.world.music_playing,
                "track_hint": self.world.track_hint,
            },
            "last_decision": self.last_decision.to_dict() if self.last_decision else None,
            "history": list(self.history[-8:]),
            "message": message,
        }


# Process-local routers keyed by username.
_routers: dict[str, ContextRouter] = {}


def get_context_router(username: str) -> ContextRouter:
    key = (username or "").strip().lower() or "_anon"
    router = _routers.get(key)
    if router is None:
        router = ContextRouter(username=key)
        _routers[key] = router
    return router


def reset_context_router(username: str) -> None:
    key = (username or "").strip().lower() or "_anon"
    _routers.pop(key, None)


def phone_queue_event(action: IntentAction, *, label: str) -> dict[str, Any]:
    """Demo / bridge event for Telefono live queue (no external call API)."""

    return {
        "at": _utc_now(),
        "action": f"context.{action}",
        "label": label,
        "source": "context_router",
    }
