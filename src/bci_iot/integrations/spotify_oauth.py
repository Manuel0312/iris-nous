"""Spotify OAuth helpers (Authorization Code + refresh)."""

from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx

AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
ME_URL = "https://api.spotify.com/v1/me"

# Playback control requires Premium; user-read-email is for display name only.
SCOPES = "user-modify-playback-state user-read-playback-state user-read-email"


def spotify_configured() -> bool:
    import os

    return bool(os.getenv("BCI_IOT_SPOTIFY_CLIENT_ID", "").strip()) and bool(
        os.getenv("BCI_IOT_SPOTIFY_CLIENT_SECRET", "").strip()
    )


def client_id() -> str:
    import os

    return os.getenv("BCI_IOT_SPOTIFY_CLIENT_ID", "").strip()


def client_secret() -> str:
    import os

    return os.getenv("BCI_IOT_SPOTIFY_CLIENT_SECRET", "").strip()


def redirect_uri(request_base: str) -> str:
    import os

    configured = os.getenv("BCI_IOT_SPOTIFY_REDIRECT_URI", "").strip()
    if configured:
        return configured
    return f"{request_base.rstrip('/')}/auth/spotify/callback"


def public_site_url(request_base: str) -> str:
    import os

    configured = os.getenv("BCI_IOT_PUBLIC_URL", "").strip()
    if configured:
        return configured.rstrip("/")
    return request_base.rstrip("/")


def new_oauth_state() -> str:
    return secrets.token_urlsafe(24)


def authorize_url(*, redirect: str, state: str) -> str:
    params = {
        "client_id": client_id(),
        "response_type": "code",
        "redirect_uri": redirect,
        "scope": SCOPES,
        "state": state,
        "show_dialog": "false",
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def _basic_auth_header() -> str:
    raw = f"{client_id()}:{client_secret()}".encode()
    return "Basic " + base64.b64encode(raw).decode()


def exchange_code(code: str, *, redirect: str) -> dict:
    with httpx.Client(timeout=15.0) as client:
        response = client.post(
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect,
            },
            headers={
                "Authorization": _basic_auth_header(),
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        response.raise_for_status()
        return response.json()


def refresh_access_token(refresh_token: str) -> dict:
    with httpx.Client(timeout=15.0) as client:
        response = client.post(
            TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            headers={
                "Authorization": _basic_auth_header(),
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        response.raise_for_status()
        return response.json()


def fetch_me(access_token: str) -> dict:
    with httpx.Client(timeout=15.0) as client:
        response = client.get(
            ME_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return response.json()


def token_expiry_iso(expires_in: int) -> str:
    return (
        datetime.now(timezone.utc) + timedelta(seconds=max(30, int(expires_in) - 60))
    ).replace(microsecond=0).isoformat()


def pairing_qr_url(target: str) -> str:
    """External QR image (no extra dependency)."""
    from urllib.parse import quote

    return (
        "https://api.qrserver.com/v1/create-qr-code/"
        f"?size=220x220&data={quote(target, safe='')}"
    )


def fingerprint_token(token: str) -> str:
    if not token:
        return ""
    return hashlib.sha256(token.encode()).hexdigest()[:12]
