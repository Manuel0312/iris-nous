"""API test for the impulse demo endpoint."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from bci_iot.web import create_app


def test_home_page_is_responsive_shell(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="home-secret")
    client = TestClient(app)
    page = client.get("/")
    assert page.status_code == 200
    assert "Iris" in page.text
    assert "Iris Nous" in page.text
    assert "unito-di.png" in page.text
    assert "pensa," in page.text
    assert "agisci," in page.text
    assert "crea." in page.text
    assert "pensando" in page.text or "Siri" in page.text
    assert 'name="viewport"' in page.text
    assert "manifest.webmanifest" in page.text


def test_demo_page_and_impulse_api(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="demo-secret")
    client = TestClient(app)

    page = client.get("/demo")
    assert page.status_code == 200
    assert "ACCENDI" in page.text

    fired = client.post("/api/demo/impulse", json={"command": "SPEGNI"})
    assert fired.status_code == 200
    body = fired.json()
    assert body["command"] == "SPEGNI"
    assert "classified_intent" in body
    assert "features" in body
