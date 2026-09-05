"""Phone call intent stub (software event; OS integration later)."""

from __future__ import annotations

from bci_iot.types import ActionCommand


class PhoneClient:
    """Record accept/reject call intents. Real telephony is platform-specific."""

    def __init__(self, *, dry_run: bool = True) -> None:
        self.dry_run = dry_run
        self.history: list[ActionCommand] = []

    def execute(self, command: ActionCommand) -> dict[str, str]:
        self.history.append(command)
        return {
            "status": "ok",
            "dry_run": "true" if (self.dry_run or command.dry_run) else "false",
            "name": command.name,
            "note": "phone bridge not bound to OS yet",
        }
