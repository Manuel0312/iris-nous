"""Intent router: finite-state mapping from neural intents to actions."""

from __future__ import annotations

from bci_iot.router.actions import command_from_action_string, resolve_profile_action
from bci_iot.router.fsm import IntentRouter

__all__ = [
    "IntentRouter",
    "command_from_action_string",
    "resolve_profile_action",
]
