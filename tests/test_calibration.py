"""Tests for headset hub (/cuffia) + setup-without-colours flow."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bci_iot.pipeline.calibration_wizard import CALIBRATION_COLORS, CalibrationSession
from bci_iot.pipeline.headset_agent import IMPULSE_KIND_ALIASES, get_headset_agent
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


def test_yes_no_impulse_aliases() -> None:
    assert IMPULSE_KIND_ALIASES["SI"] == "RISPONDI"
    assert IMPULSE_KIND_ALIASES["NO"] == "RIFIUTA"
    assert IMPULSE_KIND_ALIASES["YES"] == "RISPONDI"


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


def _register_ready(client: TestClient, app) -> None:
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
    _register_ready(client, app)

    page = client.get("/cuffia")
    assert page.status_code == 200
    assert "La tua cuffia" in page.text or "Associazione" in page.text
    assert "agent-power-on" in page.text
    assert "yn-si-btn" not in page.text

    stage1 = client.get("/cuffia?stage=1")
    assert stage1.status_code == 200
    assert "Agente cuffia" in stage1.text
    assert "Vai alla calibrazione" in stage1.text
    assert "Simulata (BrainFlow)" in stage1.text

    stage2 = client.get("/cuffia?stage=2")
    assert stage2.status_code == 200
    assert "Pensa SÌ" in stage2.text
    assert "Pensa NO" in stage2.text
    assert "yn-si-btn" in stage2.text
    assert "setup-finish" in stage2.text
    assert "/telefono-setup" in stage2.text
    assert "Il tuo telefono" in stage2.text

    # Legacy /calibrazione redirects into the hub.
    legacy1 = client.get("/calibrazione?passo=1", follow_redirects=False)
    assert legacy1.status_code == 303
    assert legacy1.headers["location"] == "/cuffia?stage=1"
    legacy2 = client.get("/calibrazione?passo=3", follow_redirects=False)
    assert legacy2.status_code == 303
    assert legacy2.headers["location"] == "/cuffia?stage=2"

    saved = client.post(
        "/api/headset/configure",
        json={"mode": "simulated", "headset_id": "cuffia-maria"},
    )
    assert saved.status_code == 200
    assert saved.json()["headset"]["mode"] == "simulated"

    intro = client.get("/inizia")
    assert intro.status_code == 200
    assert "/cuffia" in intro.text

    assert client.post("/api/headset/power", json={"on": True}).status_code == 200
    assert client.post("/api/headset/wear", json={"on_head": True}).status_code == 200

    for kind in ("SI", "NO", "SI"):
        imp = client.post("/api/headset/impulse", json={"kind": kind})
        assert imp.status_code == 200
        body = imp.json()
        assert body["impulse"]["kind"] == kind
        assert body["impulse"]["signal_source"] in {
            "physionet_corpus",
            "prior_fallback",
            "brainflow_impulse",
            "brainflow_synthetic",
        }
        assert body["impulse"]["features"]

    agent = get_headset_agent(
        username="maria",
        headset_id="cuffia-maria",
        data_root=tmp_path,
    )
    resolved = agent._resolve_prior_kind("SI")
    assert resolved == "RISPONDI"
    assert agent._resolve_prior_kind("NO") == "RIFIUTA"

    fin = client.post("/api/calibrate/complete-setup")
    assert fin.status_code == 200
    assert fin.json()["status"] == "ok"

    done = client.get("/cuffia?done=1")
    assert done.status_code == 200
    assert "Cuffia pronta" in done.text or "Calibrazione avvenuta" in done.text

    dash = client.get("/dashboard")
    assert dash.status_code == 200
    assert "Ciao, Maria" in dash.text
    assert "/cuffia" in dash.text

    profile_page = client.get("/telefono-setup?stage=1")
    assert profile_page.status_code == 200
    assert "Codice" in profile_page.text

    legacy_pair = client.get("/associa-telefono", follow_redirects=False)
    assert legacy_pair.status_code == 303
    assert legacy_pair.headers["location"].startswith("/telefono-setup")

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
    assert paired.status_code in {200, 302, 303}
    assert profiles.get("maria").phone_paired is True

    again = client.get("/telefono-setup?done=1")
    assert "associato" in again.text.lower()
