"""Virtual headset one-tap ready + companion message → In ascolto."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from bci_iot.pipeline.context_router import get_context_router, reset_context_router
from bci_iot.web import create_app


def _register(client: TestClient, store, name: str = "virt_u") -> None:
    client.post(
        "/register",
        data={"username": name, "email": f"{name}@gmail.com", "password": "VirtPass12"},
        follow_redirects=False,
    )
    p = store.get(name)
    assert p is not None
    p.email_verified = True
    store.save(p)
    client.post(
        "/anagrafica",
        data={
            "first_name": "Virt",
            "last_name": "User",
            "gender": "male",
            "email": f"{name}@gmail.com",
            "phone_country": "IT",
            "phone_national": "3331112233",
            "phone_label": "Phone",
        },
        follow_redirects=False,
    )


def test_virtual_ready_one_tap(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="virt-ready")
    client = TestClient(app)
    store = app.state.store
    _register(client, store)
    store.ensure_headset_pairing("virt_u")
    store.mark_calibration_complete("virt_u")

    before = client.get("/api/headset/agent")
    assert before.status_code == 200
    assert before.json()["agent"]["ready_for_impulses"] is False

    ready = client.post("/api/headset/virtual-ready")
    assert ready.status_code == 200, ready.text
    agent = ready.json()["agent"]
    assert agent["power"] == "on"
    assert agent["wear"] == "on_head"
    assert agent["contact_ok"] is True
    assert agent["ready_for_impulses"] is True

    status = client.get("/api/context/status")
    assert status.status_code == 200
    hs = status.json()["headset"]
    assert hs["ready_for_impulses"] is True

    cuffia = client.get("/cuffia")
    assert cuffia.status_code == 200
    assert "Indossa cuffia virtuale" in cuffia.text
    contesto = client.get("/contesto")
    assert contesto.status_code == 200
    assert "Indossa cuffia virtuale" in contesto.text


def test_companion_message_reaches_context(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="virt-msg")
    client = TestClient(app)
    _register(client, app.state.store, "msg_u")
    reset_context_router("msg_u")

    profile = app.state.store.ensure_headset_pairing("msg_u")
    code = profile.pairing_code
    client.post("/api/auth/logout")
    pair = client.post(
        "/api/companion/pair",
        json={"username": "msg_u", "password": "VirtPass12", "code": code},
    )
    assert pair.status_code == 200, pair.text
    token = pair.json()["device_token"]
    headers = {"Authorization": f"Bearer {token}"}

    incoming = client.post(
        "/api/companion/event",
        headers=headers,
        json={"event": "message_incoming", "caller": "Sara"},
    )
    assert incoming.status_code == 200, incoming.text
    assert get_context_router("msg_u").world.unread_message is True
    assert get_context_router("msg_u").active_focus() == "message"
