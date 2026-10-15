"""Local worker → cloud intent bridge (unit + API smoke)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from bci_iot.pipeline.cloud_bridge import intent_label_to_yes_no
from bci_iot.pipeline.context_router import reset_context_router
from bci_iot.types import IntentLabel
from bci_iot.web import create_app


def test_intent_label_to_yes_no() -> None:
    assert intent_label_to_yes_no(IntentLabel.ACCEPT) == "SI"
    assert intent_label_to_yes_no(IntentLabel.REJECT) == "NO"
    assert intent_label_to_yes_no("FOCUS") is None


def test_companion_intent_api(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="bridge")
    client = TestClient(app)
    client.post(
        "/register",
        data={
            "username": "worker",
            "email": "worker@gmail.com",
            "password": "Segreta123",
        },
        follow_redirects=False,
    )
    store = app.state.store
    profile = store.get("worker")
    assert profile is not None
    profile.email_verified = True
    store.save(profile)
    client.post(
        "/anagrafica",
        data={
            "first_name": "Worker",
            "last_name": "Test",
            "gender": "male",
            "email": "worker@gmail.com",
            "phone_country": "IT",
            "phone_national": "3339998877",
            "phone_label": "PC",
        },
        follow_redirects=False,
    )
    reset_context_router("worker")
    paired = store.ensure_headset_pairing("worker")
    code = paired.pairing_code
    client.post("/api/auth/logout")
    pair = client.post(
        "/api/companion/pair",
        json={"username": "worker", "password": "Segreta123", "code": code},
    )
    assert pair.status_code == 200, pair.text
    token = pair.json()["device_token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert (
        client.post(
            "/api/companion/event",
            headers=headers,
            json={"event": "music_playing", "track": "Demo"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/companion/event",
            headers=headers,
            json={"event": "message_incoming", "caller": "Sara"},
        ).status_code
        == 200
    )

    intent = client.post(
        "/api/companion/intent",
        headers=headers,
        json={"answer": "SI", "source": "local_worker", "meta": {"confidence": 0.9}},
    )
    assert intent.status_code == 200, intent.text
    body = intent.json()
    assert body["status"] == "ok"
    assert body.get("via") == "local_worker"
    # First SI after interrupt = gate ack (noop), not open_message.
    assert body["decision"]["action"] == "noop"
    assert body.get("gate_acked") is True
