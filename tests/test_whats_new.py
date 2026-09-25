"""What's New popup smoke test."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from bci_iot import __version__
from bci_iot.web import create_app
from bci_iot.web.whats_new import whats_new_payload


def test_whats_new_payload_has_version_and_items() -> None:
    payload = whats_new_payload()
    assert payload["version"] == __version__
    assert payload["intro"]
    assert len(payload["entries"]) >= 1
    assert all(item["title"] and (item.get("fix") or item.get("body")) for item in payload["entries"])
    assert all(item.get("problem") for item in payload["entries"])


def test_home_shows_novita_button(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="whats-new")
    page = TestClient(app).get("/", headers={"Accept-Language": "it-IT"})
    assert page.status_code == 200
    assert "whats-new-open" in page.text
    assert "Novità" in page.text
    assert f"Versione {__version__}" in page.text or __version__ in page.text
    assert "Meno confusione mentre scorri" in page.text
    assert "whats-new-problem" not in page.text
    assert "Versioni precedenti" in page.text or "whats-new-history" in page.text
