"""Context-switch handler for router.set_context commands."""

from __future__ import annotations

from bci_iot.router.fsm import IntentRouter
from bci_iot.types import ActionCommand, ActionContext


class RouterControlClient:
    """Apply ``router.set_context`` actions onto a live :class:`IntentRouter`."""

    def __init__(self, router: IntentRouter) -> None:
        self.router = router
        self.history: list[ActionCommand] = []

    def execute(self, command: ActionCommand) -> dict[str, str]:
        self.history.append(command)
        if command.name != "router.set_context":
            return {"status": "ignored", "name": command.name}
        raw = str(command.payload.get("context", ActionContext.IDLE.value))
        self.router.set_context(ActionContext(raw))
        return {"status": "ok", "context": self.router.context.value}
