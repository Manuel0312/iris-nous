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
    assert body["limits"]["cellular_answer_reject_android"] is True
    assert body["limits"]["cellular_answer_reject_ios"] is False
    assert body["limits"]["callkit_answer_reject_ios"] is True

    headers = {"Authorization": f"Bearer {token}"}
    beat = client.post("/api/companion/heartbeat", headers=headers)
    assert beat.status_code == 200
    beat_body = beat.json()
    assert beat_body["status"] == "ok"
    assert "ecosystem" in beat_body
    assert beat_body["ecosystem"]["telefono"]["done"] is True
    assert "cuffia" in beat_body["ecosystem"]
    assert "canali" in beat_body["ecosystem"]
    assert "calibration_complete" in beat_body
    assert "headset_linked" in beat_body

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
    assert 'href="/app/android"' in page.text
    assert "PIN di associazione" in page.text or "Collega il telefono" in page.text


def test_companion_call_reaches_context_status(tmp_path: Path) -> None:
    """APK event must persist so /api/context/status (PC In ascolto) sees the call."""

    app = create_app(data_dir=tmp_path, session_secret="bridge-call")
    client = TestClient(app)
    _register(client)
    reset_context_router("maria")

    profile = app.state.store.ensure_headset_pairing("maria")
    code = profile.pairing_code
    client.post("/api/auth/logout")
    pair = client.post(
        "/api/companion/pair",
        json={"username": "maria", "password": "Segreta123", "code": code},
    )
    token = pair.json()["device_token"]
    headers = {"Authorization": f"Bearer {token}"}

    incoming = client.post(
        "/api/companion/event",
        headers=headers,
        json={"event": "call_incoming", "caller": "Luca"},
    )
    assert incoming.status_code == 200

    # Fresh session as website user on PC
    client.post(
        "/api/auth/login",
        json={"username": "maria", "password": "Segreta123"},
    )
    # HTML form login if JSON login unavailable
    client.post(
        "/login",
        data={"username": "maria", "password": "Segreta123"},
        follow_redirects=False,
    )
    status = client.get("/api/context/status")
    assert status.status_code == 200, status.text
    body = status.json()
    assert body["active_contexts"]["call"] is True
    assert body["world"]["incoming_call"] is True


def test_companion_pwa_routes(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="pwa-app")
    client = TestClient(app)

    # Browser: /app non è destinazione normale → anteprima.
    bare = client.get("/app", follow_redirects=False)
    assert bare.status_code in {303, 302}
    assert "/app/preview" in (bare.headers.get("location") or "")

    # Nativo / WebView: stessa shell della preview a schermo intero.
    app_page = client.get("/app?from=native_app")
    assert app_page.status_code == 200
    assert "shell-tabs" in app_page.text
    assert "/static/app/shell.js" in app_page.text
    assert 'data-go="iris"' in app_page.text
    assert 'data-go="links"' in app_page.text
    assert 'data-go="account"' in app_page.text
    assert "iris-photo" in app_page.text
    assert "explain-card" in app_page.text
    assert "Pensi sì o no" in app_page.text
    assert "why-copy" in app_page.text or "Serve un account" in app_page.text
    assert "settings-open" in app_page.text
    assert "settings-lang-toggle" in app_page.text
    assert "whats-new-open" in app_page.text
    assert "whats-new-dialog" in app_page.text
    assert "data-theme-choice" in app_page.text
    assert "iris-stage" in app_page.text
    assert "explain-title" in app_page.text
    assert "/lingua/" in app_page.text
    assert "next=" in app_page.text
    assert "profile-hero" in app_page.text
    assert "account-summary" in app_page.text
    assert "btn-edit-profile" in app_page.text
    assert "summary-card" in app_page.text
    assert "phone-cc-btn" in app_page.text
    assert "phone-cc-menu" in app_page.text
    assert 'name="phone_country"' in app_page.text
    assert 'name="phone_country" type="text"' not in app_page.text
    assert 'data-iso="IT"' in app_page.text
    assert 'data-dial="+39"' in app_page.text
    # Language switch must re-render translated shell (not Italian-only hardcode).
    client.get("/lingua/en?next=/app?from=native_app", follow_redirects=True)
    en_app = client.get("/app?from=native_app")
    assert en_app.status_code == 200
    assert "whats-new-open" in en_app.text
    assert ("What's New" in en_app.text) or ("What’s New" in en_app.text)
    assert "Settings" in en_app.text
    assert "Connections" in en_app.text
    assert "Think yes or no" in en_app.text
    assert "Sign in or sign up" in en_app.text
    assert "Impostazioni" not in en_app.text
    assert "form-login" in app_page.text
    assert "form-register" in app_page.text
    assert "form-profile" in app_page.text
    assert "Connessioni" in app_page.text
    assert "Account" in app_page.text
    assert "apple-mobile-web-app-capable" in app_page.text
    assert "/static/app/manifest.webmanifest" in app_page.text

    device = client.get("/app/device")
    assert device.status_code == 200
    assert "Collega e continua" in device.text
    assert "Codice a 6 cifre" in device.text
    assert "/static/app/app.js" in device.text

    preview = client.get("/app/preview")
    assert preview.status_code == 200
    assert "Come sarà l’app" in preview.text
    assert "phone-screen" in preview.text
    assert "shell-tabs" in preview.text
    assert "iris-photo" in preview.text
    assert "form-login" in preview.text
    assert "/static/app/shell.js" in preview.text
    assert "/static/app/shell.css" in preview.text
    assert "app-frame" not in preview.text

    android = client.get("/app/android")
    assert android.status_code == 200
    assert "IrisNous.apk" in android.text or "APK" in android.text
    assert "Porta Iris con te" in android.text

    guide = client.get("/app/installa")
    assert guide.status_code == 200
    assert "Sideloadly" in guide.text or "anteprima" in guide.text.lower()
    assert "/app/preview" in guide.text
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
