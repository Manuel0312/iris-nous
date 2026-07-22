"""Phone association + music bridge tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from bci_iot.web import create_app


def _register(client: TestClient, username: str = "maria") -> None:
    client.post(
        "/register",
        data={"username": username, "password": "Segreta123"},
        follow_redirects=False,
    )
    client.post(
        "/anagrafica",
        data={
            "first_name": "Maria",
            "last_name": "Rossi",
            "gender": "female",
            "phone_label": "iPhone",
        },
        follow_redirects=False,
    )


def test_phone_pairing_and_heartbeat(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="pair-secret")
    client = TestClient(app)
    _register(client)

    page = client.get("/associa-telefono")
    assert page.status_code == 200
    assert "Codice a 6 cifre" in page.text
    assert "Telefono in linea" in page.text

    # Wrong code
    bad = client.post("/associa-telefono", data={"code": "000000"}, follow_redirects=False)
    assert bad.status_code in {303, 302}

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

    live = client.get("/telefono")
    assert live.status_code == 200
    assert "Telefono in linea" in live.text

    beat = client.post("/api/phone/heartbeat")
    assert beat.status_code == 200
    body = beat.json()
    assert body["status"] == "ok"

    music = client.post("/api/music/next")
    assert music.status_code == 200
    payload = music.json()
    assert payload["status"] == "error"
    assert "Spotify" in payload["detail"]


def test_public_dict_hides_spotify_tokens(tmp_path: Path) -> None:
    from bci_iot.accounts.store import ProfileStore

    store = ProfileStore(tmp_path)
    store.create_account("luca", "Segreta123")
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
