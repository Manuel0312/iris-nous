"""Parse dotted action strings from a user profile action_map."""

from __future__ import annotations

from bci_iot.types import ActionCommand, IntentLabel


def command_from_action_string(
    action: str,
    *,
    dry_run: bool = True,
    payload: dict[str, str] | None = None,
) -> ActionCommand:
    """Convert ``spotify.next_track`` into an :class:`ActionCommand`."""

    action = action.strip()
    if not action:
        raise ValueError("action string must be non-empty")
    target = action.split(".", 1)[0]
    return ActionCommand(
        name=action,
        target=target,
        payload=dict(payload or {}),
        dry_run=dry_run,
    )


def resolve_profile_action(
    action_map: dict[str, str],
    label: IntentLabel,
    *,
    dry_run: bool = True,
) -> ActionCommand | None:
    """Look up ``label`` in ``action_map`` and build a command if present."""

    raw = action_map.get(label.value) or action_map.get(label.value.lower())
    if not raw:
        return None
    return command_from_action_string(raw, dry_run=dry_run)
