"""Tests for Home Assistant / Spotify / phone clients in dry-run mode."""

from __future__ import annotations

from bci_iot.integrations import HomeAssistantClient, PhoneClient, SpotifyClient
from bci_iot.types import ActionCommand


def test_home_assistant_dry_run() -> None:
    client = HomeAssistantClient(dry_run=True)
    result = client.execute(
        ActionCommand(
            name="home_assistant.toggle",
            target="home_assistant",
            payload={"entity_id": "light.desk"},
        )
    )
    assert result["dry_run"] == "true"
    assert len(client.history) == 1


def test_spotify_dry_run() -> None:
    client = SpotifyClient(dry_run=True)
    result = client.execute(ActionCommand(name="spotify.next_track", target="spotify"))
    assert result["status"] == "ok"
    assert result["dry_run"] == "true"


def test_phone_records_accept() -> None:
    client = PhoneClient(dry_run=True)
    result = client.execute(ActionCommand(name="phone.accept_call", target="phone"))
    assert result["name"] == "phone.accept_call"
    assert client.history[0].name == "phone.accept_call"
