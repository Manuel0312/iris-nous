"""Home Assistant REST client."""

from __future__ import annotations

import httpx

from bci_iot.types import ActionCommand


class HomeAssistantClient:
    """Call Home Assistant services over HTTP, or dry-run without network."""

    def __init__(
        self,
        base_url: str = "",
        token: str = "",
        *,
        dry_run: bool = True,
        timeout_s: float = 5.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.dry_run = dry_run
        self.timeout_s = timeout_s
        self.history: list[ActionCommand] = []

    def execute(self, command: ActionCommand) -> dict[str, str]:
        self.history.append(command)
        if self.dry_run or command.dry_run:
            return {"status": "ok", "dry_run": "true", "name": command.name}

        if not self.base_url or not self.token:
            raise RuntimeError("Home Assistant URL/token missing (set env or disable dry_run)")

        domain, _, service = command.name.partition(".")
        if domain != "home_assistant":
            # Allow names like home_assistant.toggle → service toggle on domain light/switch
            service = command.name.split(".")[-1]
        entity_id = str(command.payload.get("entity_id", ""))
        if not entity_id:
            raise ValueError("home_assistant commands require payload.entity_id")

        ha_domain = entity_id.split(".", 1)[0]
        url = f"{self.base_url}/api/services/{ha_domain}/{service}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self.timeout_s) as client:
            response = client.post(url, headers=headers, json={"entity_id": entity_id})
            response.raise_for_status()
        return {"status": "ok", "dry_run": "false", "name": command.name, "http": str(response.status_code)}
