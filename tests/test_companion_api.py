"""Flutter companion API: pair token + call/music ingest → context_router."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from bci_iot.pipeline.context_router import get_context_router, reset_context_router
from bci_iot.web import create_app


def _register(client: TestClient, username: str = "maria") -> None:
    client.post(
        "/register",
        data={
            "username": username,
            "email": f"{username}@gmail.com",
            "password": "Segreta123",
        },
        follow_redirects=False,
    )
    store = client.app.state.store
    profile = store.get(username)
    assert profile is not None
    profile.email_verified = True
    store.save(profile)
    client.post(
        "/anagrafica",
        data={
            "first_name": "Maria",
            "last_name": "Rossi",
            "gender": "female",
            "email": f"{username}@gmail.com",
            "phone_country": "IT",
            "phone_national": "3331234567",
            "phone_label": "Pixel",
        },
        follow_redirects=False,
    )


def test_companion_pair_and_call_events(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="companion-secret")
    client = TestClient(app)
    _register(client)
    reset_context_router("maria")

    profile = app.state.store.ensure_headset_pairing("maria")
    code = profile.pairing_code
    assert len(code) == 6

    # Pair without relying on browser session cookie jar quirks: credentials + code.
    client.post("/api/auth/logout")
    pair = client.post(
        "/api/companion/pair",
        json={"username": "maria", "password": "Segreta123", "code": code},
    )
    assert pair.status_code == 200, pair.text
    body = pair.json()
    token = body["device_token"]
    assert token
    assert body["phone_paired"] is True
    assert body["limits"]["cellular_answer_reject"] is False

    headers = {"Authorization": f"Bearer {token}"}
    beat = client.post("/api/companion/heartbeat", headers=headers)
    assert beat.status_code == 200
    assert beat.json()["status"] == "ok"

    incoming = client.post(
        "/api/companion/event",
        headers=headers,
        json={"event": "call_incoming", "caller": "Luca"},
    )
    assert incoming.status_code == 200
    assert get_context_router("maria").world.incoming_call is True
    assert get_context_router("maria").world.caller_name == "Luca"
    assert get_context_router("maria").active_focus() == "call"

    ended = client.post(
        "/api/companion/event",
        headers=headers,
        json={"event": "call_ended"},
    )
    assert ended.status_code == 200
    assert get_context_router("maria").world.incoming_call is False
    assert get_context_router("maria").active_focus() == "idle"

    music = client.post(
        "/api/companion/event",
        headers=headers,
        json={"event": "music_playing", "track": "Demo track"},
    )
    assert music.status_code == 200
    assert get_context_router("maria").world.music_playing is True
    assert get_context_router("maria").active_focus() == "music"


def test_telefono_setup_mentions_companion_app(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="hub-app")
    client = TestClient(app)
    _register(client)
    page = client.get("/telefono-setup?stage=1")
    assert page.status_code == 200
    assert "App companion" in page.text
    assert 'href="/app"' in page.text
    assert "/app/installa" in page.text


def test_companion_pwa_routes(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="pwa-app")
    client = TestClient(app)

    app_page = client.get("/app")
    assert app_page.status_code == 200
    assert "Associa questo telefono" in app_page.text
    assert "apple-mobile-web-app-capable" in app_page.text
    assert "/static/app/manifest.webmanifest" in app_page.text
    assert "/static/app/app.js" in app_page.text

    guide = client.get("/app/installa")
    assert guide.status_code == 200
    assert "Aggiungi a Home" in guide.text
    assert "Safari" in guide.text
    assert "/app/apple" in guide.text

    apple = client.get("/app/apple")
    assert apple.status_code == 200
    assert "Apple Developer" in apple.text
    assert "TestFlight" in apple.text
    assert "com.irisnous.mobile" in apple.text

    sw = client.get("/app/sw.js")
    assert sw.status_code == 200
    assert "iris-app" in sw.text
    assert sw.headers.get("service-worker-allowed") == "/app"

    manifest = client.get("/static/app/manifest.webmanifest")
    assert manifest.status_code == 200
    assert "Iris Nous" in manifest.text
    assert '"start_url": "/app"' in manifest.text

    icon = client.get("/static/app/icon-180.png")
    assert icon.status_code == 200
    assert icon.headers["content-type"].startswith("image/png")
