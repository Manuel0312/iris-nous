"""Tests for profile action_map resolution and router overrides."""

from __future__ import annotations

from bci_iot.router import IntentRouter, command_from_action_string, resolve_profile_action
from bci_iot.types import ActionContext, ClassifiedIntent, IntentLabel


def test_command_from_action_string() -> None:
    cmd = command_from_action_string("spotify.next_track", dry_run=True)
    assert cmd.target == "spotify"
    assert cmd.name == "spotify.next_track"


def test_resolve_profile_action() -> None:
    cmd = resolve_profile_action(
        {"FOCUS": "phone.accept_call"},
        IntentLabel.FOCUS,
        dry_run=True,
    )
    assert cmd is not None
    assert cmd.name == "phone.accept_call"
    assert cmd.target == "phone"


def test_router_uses_profile_action_map() -> None:
    router = IntentRouter(
        debounce_windows=2,
        confidence_threshold=0.5,
        action_map={"FOCUS": "home_assistant.toggle"},
        dry_run=True,
    )
    router.set_context(ActionContext.MUSIC_MODE)
    intent = ClassifiedIntent(label=IntentLabel.FOCUS, confidence=0.9, timestamp_s=0.0)
    assert router.route(intent) is None
    action = router.route(intent)
    assert action is not None
    assert action.name == "home_assistant.toggle"
    assert action.payload["entity_id"] == "light.desk"
