"""Finite-state intent router with debounce and optional profile action_map."""

from __future__ import annotations

from collections import deque

from bci_iot.router.actions import resolve_profile_action
from bci_iot.types import ActionCommand, ActionContext, ClassifiedIntent, IntentLabel


class IntentRouter:
    """Map classified intents to context-dependent :class:`ActionCommand` values.

    If ``action_map`` is provided (from a user profile), FOCUS/RELAX/ACCEPT/REJECT
    are resolved from that map first. Context-based defaults remain as fallback
    and for IDLE context switching.
    """

    def __init__(
        self,
        *,
        debounce_windows: int = 3,
        confidence_threshold: float = 0.55,
        initial_context: ActionContext = ActionContext.IDLE,
        action_map: dict[str, str] | None = None,
        dry_run: bool = True,
        default_entity_id: str = "light.desk",
    ) -> None:
        if debounce_windows < 1:
            raise ValueError("debounce_windows must be >= 1")
        self.debounce_windows = debounce_windows
        self.confidence_threshold = confidence_threshold
        self.context = initial_context
        self.action_map = dict(action_map or {})
        self.dry_run = dry_run
        self.default_entity_id = default_entity_id
        self._history: deque[IntentLabel] = deque(maxlen=debounce_windows)

    def set_context(self, context: ActionContext) -> None:
        """Switch action context (e.g. music vs lights)."""

        self.context = context
        self._history.clear()

    def set_action_map(self, action_map: dict[str, str]) -> None:
        """Replace the profile-driven action map."""

        self.action_map = dict(action_map)

    def route(self, intent: ClassifiedIntent) -> ActionCommand | None:
        """Return an action command, or ``None`` if debounce/confidence blocks it."""

        if intent.confidence < self.confidence_threshold:
            return None

        self._history.append(intent.label)
        if len(self._history) < self.debounce_windows:
            return None

        min_votes = self.debounce_windows // 2 + 1
        if self._history.count(intent.label) < min_votes:
            return None

        return self._map_intent(intent.label)

    def _map_intent(self, label: IntentLabel) -> ActionCommand | None:
        if label == IntentLabel.IDLE:
            return None

        # Profile overrides for direct neural actions (skip while choosing context).
        if self.context != ActionContext.IDLE and self.action_map:
            mapped = resolve_profile_action(self.action_map, label, dry_run=self.dry_run)
            if mapped is not None:
                if mapped.target == "home_assistant" and "entity_id" not in mapped.payload:
                    return ActionCommand(
                        name=mapped.name,
                        target=mapped.target,
                        payload={"entity_id": self.default_entity_id},
                        dry_run=mapped.dry_run,
                    )
                return mapped

        if self.context == ActionContext.MUSIC_MODE:
            if label == IntentLabel.FOCUS:
                return ActionCommand(
                    name="spotify.next_track",
                    target="spotify",
                    dry_run=self.dry_run,
                )
            if label == IntentLabel.RELAX:
                return ActionCommand(
                    name="spotify.pause",
                    target="spotify",
                    dry_run=self.dry_run,
                )

        if self.context == ActionContext.LIGHT_MODE:
            if label == IntentLabel.FOCUS:
                return ActionCommand(
                    name="home_assistant.toggle",
                    target="home_assistant",
                    payload={"entity_id": self.default_entity_id},
                    dry_run=self.dry_run,
                )
            if label == IntentLabel.RELAX:
                return ActionCommand(
                    name="home_assistant.turn_off",
                    target="home_assistant",
                    payload={"entity_id": self.default_entity_id},
                    dry_run=self.dry_run,
                )

        if self.context == ActionContext.CALL_MODE:
            if label == IntentLabel.ACCEPT:
                return ActionCommand(
                    name="phone.accept_call",
                    target="phone",
                    dry_run=self.dry_run,
                )
            if label == IntentLabel.REJECT:
                return ActionCommand(
                    name="phone.reject_call",
                    target="phone",
                    dry_run=self.dry_run,
                )

        if self.context == ActionContext.IDLE:
            if label == IntentLabel.FOCUS:
                return ActionCommand(
                    name="router.set_context",
                    target="router",
                    payload={"context": ActionContext.MUSIC_MODE.value},
                    dry_run=self.dry_run,
                )
            if label == IntentLabel.RELAX:
                return ActionCommand(
                    name="router.set_context",
                    target="router",
                    payload={"context": ActionContext.LIGHT_MODE.value},
                    dry_run=self.dry_run,
                )

        return None
