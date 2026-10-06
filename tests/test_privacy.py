"""Privacy page and thesis disclaimer smoke tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from bci_iot.web import create_app


def test_privacy_page_and_disclaimer(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="privacy-secret")
    client = TestClient(app)

    home = client.get("/", headers={"Accept-Language": "it-IT"})
    assert home.status_code == 200
    assert "site-disclaimer" in home.text
    assert "non è un dispositivo medico" in home.text
    assert "cuffia simulata" in home.text
    assert 'href="/privacy"' in home.text
    assert "prototipo di tesi UNITO" in home.text.lower() or "Prototipo di tesi UNITO" in home.text
    assert "Controlla casa e media pensando" not in home.text

    privacy = client.get("/privacy", headers={"Accept-Language": "it-IT"})
    assert privacy.status_code == 200
    assert "Come trattiamo i dati" in privacy.text
    assert "finestre EEG pubbliche o sintetiche" in privacy.text
    assert "Non vendiamo dati cerebrali" in privacy.text
    assert "non è un dispositivo medico" in privacy.text.lower() or "Non è un dispositivo medico" in privacy.text
