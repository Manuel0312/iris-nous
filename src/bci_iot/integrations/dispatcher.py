"""Dispatch action commands to the appropriate integration client."""

from __future__ import annotations

from typing import Protocol

from bci_iot.types import ActionCommand


class IntegrationClient(Protocol):
    def execute(self, command: ActionCommand) -> dict[str, str]:
        """Execute or record an action command."""


class ActionDispatcher:
    """Route :class:`ActionCommand` objects to named integration clients."""

    def __init__(self, clients: dict[str, IntegrationClient] | None = None) -> None:
        self._clients: dict[str, IntegrationClient] = dict(clients or {})

    def register(self, target: str, client: IntegrationClient) -> None:
        self._clients[target] = client

    def dispatch(self, command: ActionCommand) -> dict[str, str]:
        client = self._clients.get(command.target)
        if client is None:
            raise KeyError(f"No integration client registered for target={command.target!r}")
        return client.execute(command)
