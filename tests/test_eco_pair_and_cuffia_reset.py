"""Ecosistema pairing session + cuffia reset after first calibration."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from bci_iot.pipeline.context_router import reset_context_router
from bci_iot.web import create_app


def _user(client: TestClient, store, name: str = "eco_user") -> None:
    client.post(
        "/register",
        data={"username": name, "email": f"{name}@gmail.com", "password": "EcoPass12"},
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
            "gender": "female",
            "email": f"{name}@gmail.com",
            "phone_country": "IT",
            "phone_national": "3330001122",
            "phone_label": "Phone",
        },
        follow_redirects=False,
    )


def test_pairing_session_mints_unique_codes(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="pair-sess")
    client = TestClient(app)
    _user(client, app.state.store)
    a = client.post("/api/telefono/pairing-session")
    assert a.status_code == 200, a.text
    code_a = a.json()["code"]
    assert len(code_a) == 6
    assert a.json()["qr_url"]
    assert a.json()["qr_payload"] == f"IRISNOUS:{code_a}"
    b = client.post("/api/telefono/pairing-session")
    assert b.status_code == 200
    code_b = b.json()["code"]
    assert code_b != code_a


def test_cuffia_reset_clears_calibration(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="cuffia-reset")
    client = TestClient(app)
    store = app.state.store
    _user(client, store, "reset_u")
    reset_context_router("reset_u")
    store.ensure_headset_pairing("reset_u")
    store.mark_calibration_complete("reset_u")
    assert store.get("reset_u").calibration_complete
    dash = client.get("/dashboard")
    assert dash.status_code == 200
    assert "eco-pair-open" in dash.text
    assert "Associazione" in dash.text
    r = client.post("/api/cuffia/reset")
    assert r.status_code == 200, r.text
    assert store.get("reset_u").calibration_complete is False
    cuffia = client.get("/cuffia")
    assert cuffia.status_code == 200
    # After reset, wizard stage (not daily-only done page)
    assert "Associazione" in cuffia.text or "Calibrazione" in cuffia.text
    assert "Ripristina" not in cuffia.text or "stage" in cuffia.text


def test_anagrafica_without_superfluous_hints(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="anag-trim")
    client = TestClient(app)
    _user(client, app.state.store, "trim_u")
    page = client.get("/anagrafica")
    assert page.status_code == 200
    assert "Va bene anche dopo" not in page.text
    assert "Scegli come preferisci essere chiamata" not in page.text
    assert "Il cambio password sta qui" not in page.text
