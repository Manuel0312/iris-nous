"""Build integration clients from application config / environment."""

from __future__ import annotations

from bci_iot.config import AppConfig, EnvSettings
from bci_iot.integrations.dispatcher import ActionDispatcher
from bci_iot.integrations.home_assistant import HomeAssistantClient
from bci_iot.integrations.phone import PhoneClient
from bci_iot.integrations.router_control import RouterControlClient
from bci_iot.integrations.spotify import SpotifyClient
from bci_iot.router.fsm import IntentRouter


def build_dispatcher(
    config: AppConfig,
    router: IntentRouter,
    *,
    env: EnvSettings | None = None,
    spotify_access_token: str = "",
) -> ActionDispatcher:
    """Create HA / Spotify / phone / router clients (dry-run safe by default)."""

    env = env or EnvSettings()
    dry_run = config.integrations.dry_run
    ha = HomeAssistantClient(
        base_url=config.integrations.home_assistant_url or (env.home_assistant_url or ""),
        token=env.home_assistant_token or "",
        dry_run=dry_run,
    )
    spotify = SpotifyClient(
        access_token=spotify_access_token,
        dry_run=dry_run or not config.integrations.spotify_enabled,
    )
    phone = PhoneClient(dry_run=True)
    control = RouterControlClient(router)
    return ActionDispatcher(
        {
            "home_assistant": ha,
            "spotify": spotify,
            "phone": phone,
            "router": control,
        }
    )
