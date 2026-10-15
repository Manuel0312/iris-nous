"""Ecosistema download QR + companion SÌ/NO without PC In ascolto page."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from bci_iot.pipeline.context_router import get_context_router, reset_context_router
from bci_iot.pipeline.headset_agent import get_headset_agent
from bci_iot.web import create_app


def _user(client: TestClient, store, name: str = "eco63") -> None:
    client.post(
        "/register",
        data={"username": name, "email": f"{name}@gmail.com", "password": "EcoPass63x"},
        follow_redirects=False,
    )
    p = store.get(name)
    assert p is not None
    p.email_verified = True
    store.save(p)
    client.post(
        "/anagrafica",
        data={
            "first_name": "Eco",
            "last_name": "User",
            "gender": "male",
            "email": f"{name}@gmail.com",
            "phone_country": "IT",
            "phone_national": "3334445566",
            "phone_label": "Phone",
        },
        follow_redirects=False,
    )


def test_ecosistema_shows_centered_download_qrs(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="eco-qr")
    client = TestClient(app)
    store = app.state.store
    _user(client, store)
    store.mark_calibration_complete("eco63")
    page = client.get("/ecosistema")
    assert page.status_code == 200
    assert "eco-download-qrs" in page.text
    assert "api.qrserver.com" in page.text
    assert "/app/store/android" in page.text
    assert "/app/store/ios" in page.text
    assert "Associazione" in page.text
    assert "eco-download-qr" in page.text
    assert "google-play-badge.svg" in page.text
    assert "app-store-badge.svg" in page.text
    assert "Prossimamente" in page.text
    assert "eco-headset-stage" in page.text
    assert "logo-spotify.svg" in page.text
    assert "Stato telefono" not in page.text  # not paired yet


def test_store_soon_landing(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="store-soon")
    client = TestClient(app)
    android = client.get("/app/store/android")
    assert android.status_code == 200
    assert "Prossimamente in store" in android.text
    ios = client.get("/app/store/ios")
    assert ios.status_code == 200
    assert "Prossimamente in store" in ios.text
    assert "App Store" in ios.text


def test_pairing_session_qr_payload(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="pair-qr")
    client = TestClient(app)
    _user(client, app.state.store, "pair63")
    res = client.post("/api/telefono/pairing-session")
    assert res.status_code == 200, res.text
    body = res.json()
    assert len(body["code"]) == 6
    assert body["qr_payload"] == f"IRISNOUS:{body['code']}"
    assert "qrserver.com" in body["qr_url"]
    assert body["code"] in body["qr_url"] or "IRISNOUS" in body["qr_url"]


def test_companion_decide_yes_no_without_pc_page(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="comp-decide")
    client = TestClient(app)
    store = app.state.store
    _user(client, store, "dec63")
    reset_context_router("dec63")
    profile = store.ensure_headset_pairing("dec63")
    store.mark_calibration_complete("dec63")
    agent = get_headset_agent(
        username="dec63",
        headset_id=profile.headset_id,
        data_root=store.data_root,
    )
    agent.memory.impulses = [
        {
            "kind": "SI",
            "features": [1.0, 0.05, 0.1, 0.0],
            "feature_names": ["a", "b", "c", "d"],
            "is_calibration_template": True,
            "signal_source": "prior_fallback",
            "alpha": 1.0,
            "beta": 0.05,
        },
        {
            "kind": "NO",
            "features": [0.05, 1.0, 0.0, 0.1],
            "feature_names": ["a", "b", "c", "d"],
            "is_calibration_template": True,
            "signal_source": "prior_fallback",
            "alpha": 0.05,
            "beta": 1.0,
        },
    ]
    agent.mark_calibration_complete()

    code = store.get("dec63").pairing_code
    client.post("/api/auth/logout")
    pair = client.post(
        "/api/companion/pair",
        json={"username": "dec63", "password": "EcoPass63x", "code": code},
    )
    assert pair.status_code == 200, pair.text
    token = pair.json()["device_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Heartbeat auto-prepares virtual headset
    beat = client.post("/api/companion/heartbeat", headers=headers)
    assert beat.status_code == 200
    assert beat.json()["headset"]["ready_for_impulses"] is True

    incoming = client.post(
        "/api/companion/event",
        headers=headers,
        json={"event": "call_incoming", "caller": "Anna"},
    )
    assert incoming.status_code == 200
    assert get_context_router("dec63").world.incoming_call is True

    decide = client.post(
        "/api/companion/decide",
        headers=headers,
        json={"answer": "NO"},
    )
    assert decide.status_code == 200, decide.text
    body = decide.json()
    assert body.get("classified_answer") in {"SI", "NO", "SÌ"}
    # Call focus should clear after reject path
    assert get_context_router("dec63").world.incoming_call is False
    # OS reject queued for Android companion
    pending = (body.get("companion") or {}).get("pending_commands") or []
    assert any(c.get("action") == "os_reject_call" for c in pending)
    cmd_id = next(c["id"] for c in pending if c.get("action") == "os_reject_call")
    ack = client.post(
        "/api/companion/commands/ack",
        headers=headers,
        json={"ids": [cmd_id]},
    )
    assert ack.status_code == 200
    assert ack.json()["acked"] >= 1
    assert not any(
        c.get("id") == cmd_id for c in (ack.json().get("pending_commands") or [])
    )


def test_companion_decide_yes_opens_whatsapp_on_message(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="comp-wa")
    client = TestClient(app)
    store = app.state.store
    _user(client, store, "wa72")
    reset_context_router("wa72")
    profile = store.ensure_headset_pairing("wa72")
    store.mark_calibration_complete("wa72")
    agent = get_headset_agent(
        username="wa72",
        headset_id=profile.headset_id,
        data_root=store.data_root,
    )
    agent.memory.impulses = [
        {
            "kind": "SI",
            "features": [1.0, 0.05, 0.1, 0.0],
            "feature_names": ["a", "b", "c", "d"],
            "is_calibration_template": True,
            "signal_source": "prior_fallback",
            "alpha": 1.0,
            "beta": 0.05,
        },
        {
            "kind": "NO",
            "features": [0.05, 1.0, 0.0, 0.1],
            "feature_names": ["a", "b", "c", "d"],
            "is_calibration_template": True,
            "signal_source": "prior_fallback",
            "alpha": 0.05,
            "beta": 1.0,
        },
    ]
    agent.mark_calibration_complete()

    code = store.get("wa72").pairing_code
    client.post("/api/auth/logout")
    pair = client.post(
        "/api/companion/pair",
        json={"username": "wa72", "password": "EcoPass63x", "code": code},
    )
    assert pair.status_code == 200, pair.text
    token = pair.json()["device_token"]
    headers = {"Authorization": f"Bearer {token}"}

    incoming = client.post(
        "/api/companion/event",
        headers=headers,
        json={"event": "message_incoming", "caller": "Marco"},
    )
    assert incoming.status_code == 200
    assert get_context_router("wa72").world.unread_message is True

    decide = client.post(
        "/api/companion/decide",
        headers=headers,
        json={"answer": "SI"},
    )
    assert decide.status_code == 200, decide.text
    body = decide.json()
    execu = body.get("execution") or {}
    assert execu.get("kind") == "open_message"
    assert execu.get("open_url") == "whatsapp://"
    os_cmd = execu.get("os_command") or {}
    assert os_cmd.get("action") == "open_whatsapp"
    assert os_cmd.get("url") == "whatsapp://"
    pending = (body.get("companion") or {}).get("pending_commands") or []
    assert any(c.get("action") == "open_whatsapp" for c in pending)
    assert get_context_router("wa72").world.unread_message is False
