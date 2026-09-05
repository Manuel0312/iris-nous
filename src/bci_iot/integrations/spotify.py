"""Spotify control client (dry-run by default; optional live token)."""

from __future__ import annotations

import httpx

from bci_iot.types import ActionCommand

_SPOTIFY_PLAYER = "https://api.spotify.com/v1/me/player"


class SpotifyClient:
    """Map pipeline commands to Spotify Web API player endpoints."""

    def __init__(
        self,
        access_token: str = "",
        *,
        dry_run: bool = True,
        timeout_s: float = 5.0,
    ) -> None:
        self.access_token = access_token
        self.dry_run = dry_run
        self.timeout_s = timeout_s
        self.history: list[ActionCommand] = []

    def execute(self, command: ActionCommand) -> dict[str, str]:
        self.history.append(command)
        if self.dry_run or command.dry_run:
            return {"status": "ok", "dry_run": "true", "name": command.name}

        if not self.access_token:
            raise RuntimeError("Spotify access_token missing (OAuth) — use dry_run or set token")

        action = command.name.split(".")[-1]
        endpoint_map = {
            "next_track": ("POST", f"{_SPOTIFY_PLAYER}/next"),
            "previous_track": ("POST", f"{_SPOTIFY_PLAYER}/previous"),
            "pause": ("PUT", f"{_SPOTIFY_PLAYER}/pause"),
            "play": ("PUT", f"{_SPOTIFY_PLAYER}/play"),
        }
        if action not in endpoint_map:
            raise ValueError(f"Unsupported Spotify action: {command.name}")

        method, url = endpoint_map[action]
        headers = {"Authorization": f"Bearer {self.access_token}"}
        with httpx.Client(timeout=self.timeout_s) as client:
            response = client.request(method, url, headers=headers)
            if response.status_code == 404:
                raise RuntimeError(
                    "Nessun player Spotify attivo. Apri Spotify sul telefono e metti in play una canzone, poi riprova."
                )
            if response.status_code == 403:
                raise RuntimeError(
                    "Spotify ha rifiutato il comando (serve Premium e autorizzazione playback)."
                )
            response.raise_for_status()
        return {"status": "ok", "dry_run": "false", "name": command.name, "http": str(response.status_code)}
