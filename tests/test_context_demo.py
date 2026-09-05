"""Tests for context channels + Alexa-short confirmation demo."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from bci_iot.pipeline.context_demo import ContextDemoEngine
from bci_iot.router.channels import ChannelId
from bci_iot.web import create_app


def test_message_channel_open_apri_confirm() -> None:
    engine = ContextDemoEngine(seed=2)
    engine.event_message(app="WhatsApp", sender="Marco")
    assert ChannelId.MESSAGES in engine.gate.open_channels()

    asked = engine.fire("APRI")
    assert asked["phase"] == "confirm"
    assert "WhatsApp" in (asked["prompt"] or "")

    done = engine.fire("SI")
    assert done["phase"] == "idle"
    assert done["opened_app"] == "WhatsApp"
    assert done["unread_message"] is False


def test_accendi_disambiguation_with_no() -> None:
    engine = ContextDemoEngine(seed=3)
    first = engine.fire("ACCENDI")
    assert first["phase"] == "confirm"
    assert "luce_salotto" in (first["prompt"] or "")

    second = engine.fire("NO")
    assert second["phase"] == "confirm"
    assert "luce_cucina" in (second["prompt"] or "")

    done = engine.fire("SI")
    assert done["phase"] == "idle"
    assert done["effect"] == "on:luce_cucina"
    assert engine.gate.world.device_on["luce_cucina"] is True


def test_call_channel_closes_after_accept() -> None:
    engine = ContextDemoEngine(seed=5)
    engine.event_call(caller="Anna")
    assert ChannelId.CALL in engine.gate.open_channels()
    engine.fire("APRI")
    done = engine.fire("SI")
    assert done["effect"] == "call:accept"
    assert ChannelId.CALL not in engine.gate.open_channels()
    assert engine.gate.world.incoming_call is False


def test_message_channel_closes_on_dismiss() -> None:
    engine = ContextDemoEngine(seed=6)
    engine.event_message()
    engine.fire("APRI")
    dismissed = engine.fire("NO")  # only one candidate → cancel
    assert ChannelId.MESSAGES not in engine.gate.open_channels()
    assert "MESSAGES chiuso" in dismissed["message"]


def test_music_stays_open_after_next() -> None:
    engine = ContextDemoEngine(seed=7)
    engine.event_music(True)
    engine.fire("NEXT")
    done = engine.fire("SI")
    assert done["effect"] == "music_next"
    assert ChannelId.MUSIC in engine.gate.open_channels()


def test_context_api(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="ctx-secret")
    client = TestClient(app)

    page = client.get("/demo")
    assert page.status_code == 200
    assert "ACCENDI" in page.text

    client.post("/api/demo/context/event", json={"event": "message"})
    client.post("/api/demo/context", json={"command": "APRI"})
    done = client.post("/api/demo/context", json={"command": "SI"})
    assert done.json()["opened_app"] == "WhatsApp"
