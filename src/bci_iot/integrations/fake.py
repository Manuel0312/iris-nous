"""Dry-run / test double for external integrations."""

from __future__ import annotations

from bci_iot.types import ActionCommand


class FakeIntegrationClient:
    """Record dispatched commands without calling real network APIs."""

    def __init__(self) -> None:
        self.history: list[ActionCommand] = []

    def execute(self, command: ActionCommand) -> dict[str, str]:
        """Append ``command`` to history and acknowledge execution."""

        recorded = ActionCommand(
            name=command.name,
            target=command.target,
            payload=dict(command.payload),
            dry_run=True,
        )
        self.history.append(recorded)
        return {"status": "ok", "dry_run": "true", "name": command.name}

    def clear(self) -> None:
        self.history.clear()
