"""Spotify next-track must go through SimulatedHeadsetAgent impulse first."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from bci_iot.pipeline.headset_agent import get_headset_agent
from bci_iot.web import create_app


def _register(client: TestClient, username: str = "iris_music") -> None:
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
            "first_name": "Iris",
            "last_name": "Music",
            "gender": "female",
            "email": f"{username}@gmail.com",
            "phone_country": "IT",
            "phone_national": "3339876543",
            "phone_label": "Pixel",
        },
        follow_redirects=False,
    )


def _pair_phone(client: TestClient, username: str = "iris_music") -> None:
    store = client.app.state.store
    profile = store.get(username)
    assert profile is not None
    code = profile.pairing_code
    ok = client.post("/associa-telefono", data={"code": code}, follow_redirects=False)
    assert ok.status_code in {200, 302, 303}


def test_music_next_requires_ready_headset(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="impulse-music")
    client = TestClient(app)
    _register(client)
    _pair_phone(client)

    res = client.post("/api/music/next")
    assert res.status_code == 400
    assert "cuffia" in res.json()["detail"].lower()


def test_music_next_impulse_persists_then_spotify(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="impulse-music-ok")
    client = TestClient(app)
    _register(client)
    _pair_phone(client)

    assert client.post("/api/headset/power", json={"on": True}).status_code == 200
    wear = client.post("/api/headset/wear", json={"on_head": True})
    assert wear.status_code == 200
    assert wear.json()["agent"]["ready_for_impulses"] is True

    res = client.post("/api/music/next")
    assert res.status_code == 200
    body = res.json()
    assert body["via"] == "headset_impulse"
    assert body["impulse"]["kind"] == "NEXT_TRACK"
    assert body["impulse"]["intensity"] > 0
    assert body["agent"]["impulses_count"] >= 1
    # Spotify still not linked → action fails after successful impulse.
    assert body["status"] == "error"
    assert "Spotify" in body["detail"]

    agent = get_headset_agent(
        username="iris_music",
        headset_id=app.state.store.get("iris_music").headset_id,
        data_root=tmp_path,
    )
    kinds = [ev["kind"] for ev in agent.memory.impulses]
    assert "NEXT_TRACK" in kinds
    assert agent.memory_path.is_file()


def test_associa_telefono_shows_impulse_ux(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="impulse-ux")
    client = TestClient(app)
    _register(client)
    page = client.get("/telefono-setup?stage=2")
    assert page.status_code == 200
    assert "music-impulse-meter" in page.text
    assert "Invio impulso alla cuffia" in page.text
    assert "Spotify" in page.text
    assert "Alexa" in page.text
