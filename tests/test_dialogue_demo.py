"""Tests for MENU + SÌ/NO dialogue demo."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from bci_iot.pipeline.dialogue_demo import DialogueDemoEngine
from bci_iot.web import create_app


def test_dialogue_menu_yes_changes_track() -> None:
    engine = DialogueDemoEngine(seed=3)
    assert engine.status()["phase"] == "idle"

    opened = engine.fire("MENU")
    assert opened["phase"] == "menu"
    assert "canzone" in (opened["question"]["text"] if opened["question"] else "").lower()

    yes = engine.fire("SI")
    assert yes["phase"] == "idle"
    assert yes["effect"] == "music_next"
    assert yes["track_number"] == 2


def test_dialogue_no_skips_then_light() -> None:
    engine = DialogueDemoEngine(seed=4)
    engine.fire("MENU")
    skipped = engine.fire("NO")
    assert skipped["phase"] == "menu"
    assert "luce" in skipped["question"]["text"].lower()

    lit = engine.fire("SI")
    assert lit["effect"] == "light_on"
    assert lit["bulb_on"] is True


def test_dialogue_si_without_menu_does_nothing() -> None:
    engine = DialogueDemoEngine(seed=1)
    result = engine.fire("SI")
    assert result["phase"] == "idle"
    assert result["effect"] is None
    assert "MENU" in result["message"]


def test_dialogue_api(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="dlg-secret")
    client = TestClient(app)

    status = client.get("/api/demo/dialogue/status")
    assert status.json()["phase"] == "idle"

    client.post("/api/demo/dialogue", json={"command": "MENU"})
    done = client.post("/api/demo/dialogue", json={"command": "SI"})
    body = done.json()
    assert body["effect"] == "music_next"
    assert body["track_number"] == 2
