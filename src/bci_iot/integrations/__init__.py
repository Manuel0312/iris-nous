"""External API clients (Home Assistant, Spotify, phone, dispatcher)."""

from __future__ import annotations

from bci_iot.integrations.dispatcher import ActionDispatcher
from bci_iot.integrations.factory import build_dispatcher
from bci_iot.integrations.fake import FakeIntegrationClient
from bci_iot.integrations.home_assistant import HomeAssistantClient
from bci_iot.integrations.phone import PhoneClient
from bci_iot.integrations.spotify import SpotifyClient

__all__ = [
    "ActionDispatcher",
    "FakeIntegrationClient",
    "HomeAssistantClient",
    "PhoneClient",
    "SpotifyClient",
    "build_dispatcher",
]
