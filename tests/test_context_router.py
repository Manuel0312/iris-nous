"""Unit tests for context exclusion router + /contesto web smoke."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bci_iot.pipeline.context_router import (
    ContextRouter,
    DECISION_MATRIX,
    get_context_router,
    map_decision,
    normalize_yes_no,
    reset_context_router,
    resolve_focus,
)
from bci_iot.web import create_app


def test_priority_call_beats_message_and_music() -> None:
    assert (
        resolve_focus(incoming_call=True, unread_message=True, music_playing=True)
        == "call"
    )
    assert (
        resolve_focus(incoming_call=False, unread_message=True, music_playing=True)
        == "message"
    )
    assert (
        resolve_focus(incoming_call=False, unread_message=False, music_playing=True)
        == "music"
    )
    assert (
        resolve_focus(incoming_call=False, unread_message=False, music_playing=False)
        == "idle"
    )


def test_decision_matrix_complete() -> None:
    for focus in ("idle", "call", "message", "music"):
        for yn in ("SI", "NO"):
            assert (focus, yn) in DECISION_MATRIX
            assert map_decision(focus, yn)  # type: ignore[arg-type]


def test_music_plus_call_si_answers_call() -> None:
    r = ContextRouter(username="demo")
    r.set_music(True)
    r.simulate_call(caller="Luca")
    snap = r.focus_snapshot()
    assert snap.kind == "call"
    assert "Luca" in snap.prompt
    assert "pensa SÌ o NO" in snap.prompt
    out = r.decide("SI")
    assert out["decision"]["action"] == "answer_call"
    assert out["focus"]["kind"] == "music"  # call closed, music sticky


def test_music_plus_message_no_dismisses() -> None:
    r = ContextRouter(username="demo2")
    r.set_music(True, track="Iris Mix")
    r.simulate_message(sender="Sara", app="Telegram")
    assert r.active_focus() == "message"
    out = r.decide("NO")
    assert out["decision"]["action"] == "dismiss_message"
    assert out["focus"]["kind"] == "music"
    assert "Iris Mix" in out["focus"]["title"]


def test_music_only_si_next_no_keep() -> None:
    r = ContextRouter(username="demo3")
    r.set_music(True)
    assert r.decide("SI")["decision"]["action"] == "next_track"
    assert r.active_focus() == "music"
    assert r.decide("NO")["decision"]["action"] == "keep_track"


def test_normalize_yes_no_aliases() -> None:
    assert normalize_yes_no("sì") == "SI"
    assert normalize_yes_no("RISPONDI") == "SI"
    assert normalize_yes_no("RIFIUTA") == "NO"
    assert normalize_yes_no("NEXT_TRACK") is None


def _register(client: TestClient, username: str = "ctx_user") -> None:
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
            "first_name": "Ctx",
            "last_name": "User",
            "gender": "female",
            "email": f"{username}@gmail.com",
            "phone_country": "IT",
            "phone_national": "3331112233",
            "phone_label": "Pixel",
        },
        follow_redirects=False,
    )


def _ready_headset(client: TestClient) -> None:
    assert client.post("/api/headset/power", json={"on": True}).status_code == 200
    wear = client.post("/api/headset/wear", json={"on_head": True})
    assert wear.status_code == 200
    assert wear.json()["agent"]["ready_for_impulses"] is True


@pytest.fixture(autouse=True)
def _reset_routers() -> None:
    reset_context_router("ctx_user")
    yield
    reset_context_router("ctx_user")


def test_contesto_page_smoke(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="ctx-page")
    client = TestClient(app)
    _register(client)
    page = client.get("/contesto")
    assert page.status_code == 200
    assert "Contesto live" in page.text
    assert "Sto decidendo su" in page.text or "focus" in page.text.lower()
    assert "Simula chiamata" in page.text
    assert "Pensa SÌ" in page.text
    assert "cuffia virtuale" in page.text
    assert "calibrazione" in page.text


def test_context_api_priority_and_decide(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="ctx-api")
    client = TestClient(app)
    _register(client)
    _ready_headset(client)

    assert client.post("/api/context/live", json={"enabled": True}).status_code == 200
    client.post("/api/context/event", json={"event": "music_on"})
    client.post("/api/context/event", json={"event": "call", "caller": "Anna"})
    st = client.get("/api/context/status").json()
    assert st["focus"]["kind"] == "call"
    assert "Anna" in st["focus"]["prompt"]

    res = client.post("/api/context/decide", json={"answer": "NO"})
    assert res.status_code == 200
    body = res.json()
    assert body["decision"]["action"] == "reject_call"
    assert body["impulse"]["kind"] in {"NO", "SI"}
    assert body["focus"]["kind"] == "music"
    assert body["execution"]["kind"] == "reject_call"
    assert body["execution"]["mode"] == "phone_queue_demo"

    # Phone queue got the demo event
    queue = app.state.phone_queues.get("ctx_user") or []
    assert any(e.get("action") == "context.reject_call" for e in queue)


def test_headset_impulse_routes_when_live(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="ctx-live")
    client = TestClient(app)
    _register(client)
    _ready_headset(client)
    client.post("/api/context/live", json={"enabled": True})
    client.post("/api/context/event", json={"event": "message", "sender": "Marco"})

    res = client.post("/api/headset/impulse", json={"kind": "SI"})
    assert res.status_code == 200
    body = res.json()
    assert "context" in body
    assert body["context"]["decision"]["action"] == "open_message"


def test_dashboard_links_contesto(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="ctx-dash")
    client = TestClient(app)
    _register(client)
    page = client.get("/dashboard")
    assert page.status_code == 200
    assert 'href="/contesto"' in page.text


def test_get_context_router_cached() -> None:
    reset_context_router("cache_me")
    a = get_context_router("cache_me")
    b = get_context_router("cache_me")
    assert a is b
    a.simulate_call()
    assert b.active_focus() == "call"
    reset_context_router("cache_me")
