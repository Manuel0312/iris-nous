"""Tests for headset colour calibration wizard."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from bci_iot.pipeline.calibration_wizard import CALIBRATION_COLORS, CalibrationSession
from bci_iot.web import create_app


def test_calibration_session_capture_and_finish(tmp_path: Path) -> None:
    sess = CalibrationSession(
        username="maria",
        headset_id="cuffia-test",
        pairing_code="123456",
        samples_per_word=2,
    )
    for colour in CALIBRATION_COLORS:
        for _ in range(2):
            result = sess.capture(colour)
            assert result.intensity > 0
            assert result.command == colour
            assert result.folder
            assert result.color_name
    # Folder alias → colour
    assert sess.capture("video").command == "ROSSO"
    assert sess.complete_enough()
    path, acc = sess.finish(models_dir=tmp_path)
    assert path.exists()
    assert 0.0 <= acc <= 1.0


def test_web_calibration_flow(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="calib-secret")
    client = TestClient(app)

    client.post(
        "/register",
        data={"username": "maria", "password": "Segreta123"},
        follow_redirects=False,
    )
    client.post(
        "/anagrafica",
        data={
            "first_name": "Maria",
            "last_name": "Rossi",
            "gender": "female",
            "phone_label": "iPhone",
        },
        follow_redirects=False,
    )

    page = client.get("/calibrazione")
    assert page.status_code == 200
    assert "Associa colore e segnale" in page.text
    assert "Codice associazione" in page.text
    assert "Video" in page.text
    assert "rosso" in page.text.lower()

    for colour in CALIBRATION_COLORS:
        for _ in range(3):
            cap = client.post("/api/calibrate/capture", json={"command": colour})
            assert cap.status_code == 200
            body = cap.json()
            assert body["command"] == colour
            assert body["folder"]
            assert body["color_name"]

    fin = client.post("/api/calibrate/finish")
    assert fin.status_code == 200
    assert fin.json()["status"] == "ok"

    done = client.get("/calibrazione?done=1&acc=1")
    assert "Calibrazione avvenuta" in done.text

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

    paired = client.post(
        "/associa-telefono",
        data={"code": profile.pairing_code},
        follow_redirects=False,
    )
    assert paired.status_code == 200
    assert profiles.get("maria").phone_paired is True

    again = client.get("/associa-telefono")
    assert "associato" in again.text.lower()
