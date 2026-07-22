"""Execute music / phone actions for a linked user profile."""

from __future__ import annotations

from datetime import datetime, timezone

from bci_iot.accounts.store import ProfileStore, UserProfile
from bci_iot.integrations.spotify import SpotifyClient
from bci_iot.integrations.spotify_oauth import refresh_access_token, spotify_configured, token_expiry_iso
from bci_iot.types import ActionCommand


def ensure_fresh_spotify_token(profiles: ProfileStore, profile: UserProfile) -> UserProfile:
    """Refresh Spotify access token if expired / near expiry."""
    if not profile.spotify_linked:
        return profile
    needs_refresh = True
    if profile.spotify_access_token and profile.spotify_token_expires_at:
        try:
            expires = datetime.fromisoformat(
                profile.spotify_token_expires_at.replace("Z", "+00:00")
            )
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            needs_refresh = datetime.now(timezone.utc) >= expires
        except ValueError:
            needs_refresh = True
    if not needs_refresh:
        return profile
    if not profile.spotify_refresh_token or not spotify_configured():
        return profile
    data = refresh_access_token(profile.spotify_refresh_token)
    access = str(data.get("access_token") or "")
    refresh = str(data.get("refresh_token") or profile.spotify_refresh_token)
    expires_at = token_expiry_iso(int(data.get("expires_in") or 3600))
    return profiles.set_spotify_tokens(
        profile.username,
        access_token=access,
        refresh_token=refresh,
        expires_at=expires_at,
        user_id=profile.spotify_user_id,
        display_name=profile.spotify_display_name,
    )


def run_spotify_action(
    profiles: ProfileStore,
    profile: UserProfile,
    action: str,
    *,
    queue: list[dict] | None = None,
) -> dict:
    """
    Fire a Spotify player action for the user.

    ``action`` examples: next_track, pause, play, previous_track.
    Always records a phone-queue event when ``queue`` is provided.
    """
    name = action if action.startswith("spotify.") else f"spotify.{action}"
    short = name.split(".")[-1]
    event = {
        "at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "action": name,
        "label": {
            "next_track": "Prossima canzone",
            "previous_track": "Canzone precedente",
            "pause": "Pausa",
            "play": "Play",
        }.get(short, name),
    }
    if queue is not None:
        queue.append(event)
        del queue[:-20]

    if not profile.phone_paired:
        return {
            "status": "error",
            "detail": "Telefono non associato. Completa Associa telefono.",
            "event": event,
        }
    if not profile.spotify_linked:
        return {
            "status": "error",
            "detail": "Spotify non collegato. Collega Spotify dalla pagina Associa telefono.",
            "event": event,
        }
    if not spotify_configured():
        return {
            "status": "error",
            "detail": "Spotify non configurato sul server (mancano CLIENT_ID/SECRET).",
            "event": event,
        }

    fresh = ensure_fresh_spotify_token(profiles, profile)
    client = SpotifyClient(access_token=fresh.spotify_access_token, dry_run=False)
    try:
        result = client.execute(ActionCommand(name=name, target="spotify", dry_run=False))
    except Exception as exc:  # noqa: BLE001 — surface API errors to UI
        return {
            "status": "error",
            "detail": str(exc),
            "event": event,
        }
    stats = dict(fresh.usage_stats or {})
    stats["intents_fired"] = int(stats.get("intents_fired") or 0) + 1
    stats["last_activity"] = event["at"]
    fresh.usage_stats = stats
    profiles.save(fresh)
    return {"status": "ok", "result": result, "event": event}
