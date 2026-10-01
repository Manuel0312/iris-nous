"""Tests for headset colour calibration wizard + setup-without-colours flow."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bci_iot.pipeline.calibration_wizard import CALIBRATION_COLORS, CalibrationSession
from bci_iot.web import create_app


def test_calibration_session_capture_and_finish(tmp_path: Path) -> None:
    """Legacy colour capture path still works for API/back-compat."""

    sess = CalibrationSession(
        username="maria",
        headset_id="cuffia-test",
        pairing_code="123456",
        samples_per_word=2,
        prefer_brainflow=False,
        data_root=tmp_path,
    )
    for colour in CALIBRATION_COLORS:
        for _ in range(2):
            result = sess.capture(colour)
            assert result.intensity > 0
            assert result.command == colour
            assert result.folder
            assert result.color_name
            assert result.signal_source in {"prior_fallback", "physionet_corpus"}
    # Folder alias → colour
    assert sess.capture("video").command == "ROSSO"
    assert sess.complete_enough()
    path, acc = sess.finish(models_dir=tmp_path / "models")
    assert path.exists()
    assert 0.0 <= acc <= 1.0
    latest = tmp_path / "calibration" / "maria" / "latest.json"
    assert latest.is_file()


def test_calibration_rejects_disconnected_mode() -> None:
    sess = CalibrationSession(
        username="maria",
        headset_id="cuffia-test",
        pairing_code="123456",
        headset_mode="disconnected",
        prefer_brainflow=False,
    )
    with pytest.raises(ValueError, match="non collegata"):
        sess.capture("ROSSO")


@pytest.mark.skipif(
    __import__("bci_iot.acquisition", fromlist=["brainflow_available"]).brainflow_available()
    is False,
    reason="brainflow not installed",
)
def test_calibration_capture_brainflow_path() -> None:
    sess = CalibrationSession(
        username="maria",
        headset_id="cuffia-bf",
        pairing_code="123456",
        samples_per_word=1,
        prefer_brainflow=True,
        headset_mode="simulated",
    )
    result = sess.capture("ROSSO")
    assert result.signal_source in {"brainflow_synthetic", "brainflow_impulse", "physionet_corpus"}
    assert result.intensity > 0


def test_web_calibration_flow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "bci_iot.pipeline.calibration_wizard.brainflow_available",
        lambda: False,
    )
    monkeypatch.setattr(
        "bci_iot.pipeline.headset_agent.brainflow_available",
        lambda: False,
    )
    app = create_app(data_dir=tmp_path, session_secret="calib-secret")
    client = TestClient(app)

    client.post(
        "/register",
        data={
            "username": "maria",
            "email": "maria@gmail.com",
            "password": "Segreta123",
        },
        follow_redirects=False,
    )
    profile = app.state.store.get("maria")
    assert profile is not None
    profile.email_verified = True
    app.state.store.save(profile)
    client.post(
        "/anagrafica",
        data={
            "first_name": "Maria",
            "last_name": "Rossi",
            "gender": "female",
            "email": "maria@gmail.com",
            "phone_country": "IT",
            "phone_national": "3331234567",
            "phone_label": "iPhone",
        },
        follow_redirects=False,
    )

    page = client.get("/calibrazione")
    assert page.status_code == 200
    assert "cuffia" in page.text.lower() or "Simulata" in page.text
    cfg = client.get("/calibrazione?passo=1")
    assert cfg.status_code == 200
    assert "Agente cuffia" in cfg.text
    assert "agent-power-on" in cfg.text
    assert "agent-impulse" in cfg.text
    assert "Simulata (BrainFlow)" in cfg.text
    assert "passo=4" not in cfg.text
    assert "calib-color-tile" not in cfg.text

    saved = client.post(
        "/api/headset/configure",
        json={"mode": "simulated", "headset_id": "cuffia-maria"},
    )
    assert saved.status_code == 200
    assert saved.json()["headset"]["mode"] == "simulated"

    intro = client.get("/inizia")
    assert intro.status_code == 200
    assert "Iniziamo" in intro.text or "Pensi" in intro.text

    code = client.get("/calibrazione?passo=2")
    assert code.status_code == 200
    assert "Invia il codice" in code.text
    assert "Invia il codice via email" in code.text

    phone = client.get("/calibrazione?passo=3")
    assert phone.status_code == 200
    assert "Associa il telefono" in phone.text
    assert "setup-finish" in phone.text
    assert "Completa configurazione" in phone.text

    # Legacy passo 4 redirects conceptually to 3 (clamped).
    legacy = client.get("/calibrazione?passo=4")
    assert legacy.status_code == 200
    assert "calib-color-tile" not in legacy.text
    assert "setup-finish" in legacy.text

    # Headset ready + impulses → complete setup (no colours).
    assert client.post("/api/headset/power", json={"on": True}).status_code == 200
    assert client.post("/api/headset/wear", json={"on_head": True}).status_code == 200
    for _ in range(3):
        imp = client.post("/api/headset/impulse", json={"kind": "ACCENDI"})
        assert imp.status_code == 200
        body = imp.json()
        assert body["impulse"]["signal_source"] in {
            "physionet_corpus",
            "prior_fallback",
            "brainflow_impulse",
            "brainflow_synthetic",
        }
        assert body["impulse"]["features"]
        assert body["impulse"]["window_stats"]

    fin = client.post("/api/calibrate/complete-setup")
    assert fin.status_code == 200
    assert fin.json()["status"] == "ok"

    done = client.get("/calibrazione?done=1")
    assert "Configurazione completata" in done.text or "Calibrazione avvenuta" in done.text

    dash = client.get("/dashboard")
    assert dash.status_code == 200
    assert "Ciao, Maria" in dash.text

    profile_page = client.get("/associa-telefono")
    assert profile_page.status_code == 200
    assert "Codice" in profile_page.text

    profiles = app.state.store
    profile = profiles.get("maria")
    assert profile is not None
    assert profile.pairing_code
    assert profile.phone_paired is False
    assert profile.calibration_complete is True

    paired = client.post(
        "/associa-telefono",
        data={"code": profile.pairing_code},
        follow_redirects=False,
    )
    assert paired.status_code == 200
    assert profiles.get("maria").phone_paired is True

    again = client.get("/associa-telefono")
    assert "associato" in again.text.lower()
