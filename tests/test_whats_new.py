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
    assert (
        "Hub «Il tuo telefono»" in page.text
        or "Hub «La tua cuffia»" in page.text
        or "Privacy e chiarezza demo" in page.text
    )
    assert "Tendina con foto e icone animate" in page.text
    assert "Menu minimale e Ecosistema a step" in page.text
    assert "Ban: fuori subito, non al prossimo login" in page.text
    assert "Collegamento telefono vero (credenziale)" in page.text
    assert "Pagine telefono più chiare" in page.text
    assert "Colori soft e testo leggibile" in page.text
    assert "App /app in liquid glass" in page.text
    assert "Percorso Apple Developer → TestFlight" in page.text
    assert "Due modi sull’iPhone" in page.text
    assert "App Iris installabile sull’iPhone" in page.text
    assert "Stato e eventi dall’app" in page.text
    assert "App companion Android e iPhone" in page.text
    assert "Chiamate rilevate dall’app → In ascolto" in page.text
    assert "Telefono: associa, Spotify, ponte chiamate" in page.text
    assert "In ascolto, senza accendere nulla" in page.text
    assert "whats-new-body" in page.text
    assert "whats-new-problem" not in page.text
    assert "Versioni precedenti" in page.text or "whats-new-history" in page.text
    assert "SÌ/NO per similarità, non replay" in page.text  # previous release still listed
