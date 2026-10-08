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
    assert "PIN di associazione" in stage1.text
    assert "Collega questo telefono ora" in stage1.text
    assert "Credenziale" in stage1.text or "credenziale" in stage1.text
    assert "associa-telefono/questo-dispositivo" in stage1.text
    assert 'href="/app"' in stage1.text
    assert "Cosa è reale" in stage1.text
    assert "telefono-alexa-stub" not in stage1.text

    stage2 = client.get("/telefono-setup?stage=2")
    assert stage2.status_code == 200
    assert "Spotify" in stage2.text
    assert "telefono-alexa-stub" not in stage2.text

    legacy = client.get("/associa-telefono", follow_redirects=False)
    assert legacy.status_code == 303
    assert legacy.headers["location"].startswith("/telefono-setup")


def test_one_tap_pair_issues_device_credential(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="onetap-cred")
    client = TestClient(app)
    _register(client)

    tap = client.post(
        "/associa-telefono/questo-dispositivo",
        headers={"User-Agent": "Mozilla/5.0 (Linux; Android 14) IrisTest"},
        follow_redirects=False,
    )
    assert tap.status_code in {302, 303}
    assert "/telefono-setup?stage=2" in tap.headers.get("location", "")
    profile = app.state.store.get("maria")
    assert profile is not None
    assert profile.phone_paired is True
    assert app.state.store.companion_linked("maria") is True
    assert "Android" in (profile.phone_label or "")

    page = client.get("/telefono-setup")
    assert page.status_code == 200
    assert "Dispositivo fidato" in page.text or "Telefono collegato" in page.text


def test_one_tap_pair_and_call_bridge_on_live(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="onetap-secret")
    client = TestClient(app)
    _register(client)

    tap = client.post("/associa-telefono/questo-dispositivo", follow_redirects=False)
    assert tap.status_code in {302, 303}
    assert "/telefono-setup?stage=2" in tap.headers.get("location", "")
    profile = app.state.store.get("maria")
    assert profile is not None
    assert profile.phone_paired is True

    live = client.get("/telefono")
    assert live.status_code == 200
    assert "Arriva una chiamata" in live.text or "Telefono" in live.text

    ev = client.post("/api/context/event", json={"event": "call", "caller": "Anna"})
    assert ev.status_code == 200
    assert ev.json().get("phone_event", {}).get("kind") == "incoming_call"

    beat = client.post("/api/phone/heartbeat")
    assert beat.status_code == 200
    body = beat.json()
    assert body["status"] == "ok"
    assert body["context"]["incoming_call"] is True
    assert "Anna" in (body["context"].get("caller_name") or "")

    done = client.get("/telefono-setup?done=1")
    assert done.status_code == 200
    assert "Telefono collegato" in done.text or "Dispositivo fidato" in done.text
    assert "Spotify" in done.text


def test_phone_pairing_and_heartbeat(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="pair-secret")
    client = TestClient(app)
    _register(client)

    page = client.get("/telefono-setup?stage=1")
    assert page.status_code == 200
    assert "PIN di associazione" in page.text

    bad = client.post("/associa-telefono", data={"code": "000000"}, follow_redirects=False)
    assert bad.status_code in {303, 302}

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
    assert store.companion_linked("maria") is True

    done = client.get("/telefono-setup?done=1")
    assert done.status_code == 200
    assert "Telefono collegato" in done.text or "Dispositivo fidato" in done.text

    live = client.get("/telefono")
    assert live.status_code == 200

    beat = client.post("/api/phone/heartbeat")
    assert beat.status_code == 200
    assert beat.json()["status"] == "ok"

    music = client.post("/api/music/next")
    assert music.status_code == 400

    assert client.post("/api/headset/power", json={"on": True}).status_code == 200
    assert client.post("/api/headset/wear", json={"on_head": True}).status_code == 200
    music_ready = client.post("/api/music/next")
    assert music_ready.status_code == 200
    payload = music_ready.json()
    assert payload["status"] == "error"
    assert "Spotify" in payload["detail"]
    assert payload["via"] == "headset_impulse"


def test_pairing_code_is_emailed_and_can_be_resent(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="pair-mail")
    client = TestClient(app)
    _register(client)

    page = client.get("/telefono-setup?stage=1")
    assert page.status_code == 200
    assert "Invia il PIN via email" in page.text
    profile = app.state.store.get("maria")
    assert profile is not None
    assert profile.pairing_code

    sent = client.post("/associa-telefono/invia-codice", follow_redirects=False)
    assert sent.status_code in {302, 303}
    assert sent.headers["location"] == "/telefono-setup?stage=1"
    profile = app.state.store.get("maria")
    assert profile is not None
    assert (profile.usage_stats or {}).get("pairing_emailed_code") == profile.pairing_code

    pair = client.get("/telefono-setup?stage=1")
    assert "PIN di associazione" in pair.text

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
