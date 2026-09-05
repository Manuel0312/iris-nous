"""Tests for coloured macro-folder navigation."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from bci_iot.pipeline.macro_folders import FolderId, MacroFolderEngine
from bci_iot.web import create_app


def test_macro_folder_engine_flow() -> None:
    eng = MacroFolderEngine()
    eng.open_folder(FolderId.VIDEO)
    assert eng.phase.value == "folder"
    eng.next_app()
    eng.ask_open()
    assert eng.phase.value == "confirm"
    status = eng.confirm_yes()
    assert status["phase"] == "idle"
    assert status["last_opened"] in {"YouTube", "Twitch", "Netflix"}


def test_folders_api(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="folders-secret")
    client = TestClient(app)
    page = client.get("/cartelle")
    assert page.status_code == 200
    assert "4 colori" in page.text

    st = client.get("/api/folders/status")
    assert st.status_code == 200
    assert len(st.json()["folders"]) == 4

    opened = client.post("/api/folders", json={"command": "ROSSO"})
    assert opened.status_code == 200
    assert opened.json()["active_folder"] == "video"

    client.post("/api/folders", json={"command": "APRI"})
    yes = client.post("/api/folders", json={"command": "SI"})
    assert yes.json()["last_opened"] is not None
