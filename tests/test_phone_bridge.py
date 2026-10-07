"""Phone association + music bridge tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

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
            "phone_label": "iPhone",
        },
        follow_redirects=False,
    )


def test_phone_setup_hub_stages(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="hub-secret")
    client = TestClient(app)
    _register(client)

    stage1 = client.get("/telefono-setup?stage=1")
    assert stage1.status_code == 200
    assert "Il tuo telefono" in stage1.text
    assert "Codice a 6 cifre" in stage1.text
    assert "A cosa serve" in stage1.text
    assert "Funziona dal browser dello smartphone" in stage1.text

    stage2 = client.get("/telefono-setup?stage=2")
    assert stage2.status_code == 200
    assert "Stato e servizi" in stage2.text or "Stato del ponte" in stage2.text
    assert "Spotify" in stage2.text
    assert "Alexa" in stage2.text
    assert "Collegamento dopo" in stage2.text

    # Legacy /associa-telefono → hub
    legacy = client.get("/associa-telefono", follow_redirects=False)
    assert legacy.status_code == 303
    assert legacy.headers["location"].startswith("/telefono-setup")


def test_phone_pairing_and_heartbeat(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="pair-secret")
    client = TestClient(app)
    _register(client)

    page = client.get("/telefono-setup?stage=1")
    assert page.status_code == 200
    assert "Codice a 6 cifre" in page.text

    # Wrong code
    bad = client.post("/associa-telefono", data={"code": "000000"}, follow_redirects=False)
    assert bad.status_code in {303, 302}
    assert "/telefono-setup" in bad.headers.get("location", "")

    # Read code from profile store
    store = app.state.store
    profile = store.get("maria")
    assert profile is not None
    code = profile.pairing_code
    assert len(code) == 6

    ok = client.post("/associa-telefono", data={"code": code}, follow_redirects=False)
    assert ok.status_code in {200, 302, 303}

    profile = store.get("maria")
    assert profile is not None
    assert profile.phone_paired is True

    done = client.get("/telefono-setup?done=1")
    assert done.status_code == 200
    assert "Telefono associato" in done.text

    live = client.get("/telefono")
    assert live.status_code == 200
    assert "Telefono in linea" in live.text
    assert "browser dello smartphone" in live.text

    beat = client.post("/api/phone/heartbeat")
    assert beat.status_code == 200
    body = beat.json()
    assert body["status"] == "ok"

    music = client.post("/api/music/next")
    assert music.status_code == 400
    assert "cuffia" in music.json()["detail"].lower()

    # Prepare simulated headset, then impulse → Spotify path (Spotify still unlinked).
    assert client.post("/api/headset/power", json={"on": True}).status_code == 200
    assert client.post("/api/headset/wear", json={"on_head": True}).status_code == 200
    music_ready = client.post("/api/music/next")
    assert music_ready.status_code == 200
    payload = music_ready.json()
    assert payload["status"] == "error"
    assert "Spotify" in payload["detail"]
    assert payload["via"] == "headset_impulse"
    assert payload["impulse"]["kind"] == "NEXT_TRACK"
    assert payload["agent"]["impulses_count"] >= 1


def test_pairing_code_is_emailed_and_can_be_resent(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="pair-mail")
    client = TestClient(app)
    _register(client)

    page = client.get("/telefono-setup?stage=1")
    assert page.status_code == 200
    assert "Invia il codice via email" in page.text
    profile = app.state.store.get("maria")
    assert profile is not None
    assert profile.pairing_code
    assert (profile.usage_stats or {}).get("pairing_emailed_code") != profile.pairing_code

    sent = client.post("/associa-telefono/invia-codice", follow_redirects=False)
    assert sent.status_code in {302, 303}
    assert sent.headers["location"] == "/telefono-setup?stage=1"
    profile = app.state.store.get("maria")
    assert profile is not None
    assert (profile.usage_stats or {}).get("pairing_emailed_code") == profile.pairing_code

    pair = client.get("/telefono-setup?stage=1")
    assert "Invia il codice via email" in pair.text
    assert "Codice a 6 cifre" in pair.text

    # Legacy calibrazione passo=2 redirects into cuffia calibrazione stage.
    legacy = client.get("/calibrazione?passo=2", follow_redirects=False)
    assert legacy.status_code == 303
    assert legacy.headers["location"] == "/cuffia?stage=2"


def test_public_dict_hides_spotify_tokens(tmp_path: Path) -> None:
    from bci_iot.accounts.store import ProfileStore

    store = ProfileStore(tmp_path)
    store.create_account("luca", "Segreta123", email="luca@gmail.com")
    store.set_spotify_tokens(
        "luca",
        access_token="secret-access",
        refresh_token="secret-refresh",
        display_name="Luca",
    )
    profile = store.get("luca")
    assert profile is not None
    pub = profile.public_dict()
    assert "spotify_access_token" not in pub
    assert "spotify_refresh_token" not in pub
    assert pub["spotify_linked"] is True
