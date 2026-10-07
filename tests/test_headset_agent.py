"""Tests for SimulatedHeadsetAgent — device-like power/wear/contact/impulse + memory."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bci_iot.pipeline.headset_agent import SimulatedHeadsetAgent, get_headset_agent
from bci_iot.web import create_app


def test_agent_power_wear_contact_impulse_and_memory(tmp_path: Path) -> None:
    agent = SimulatedHeadsetAgent(
        username="maria",
        headset_id="cuffia-sim-1",
        data_root=tmp_path,
        seed=42,
    )
    assert agent.status()["power"] == "off"
    assert agent.status()["ready_for_impulses"] is False

    with pytest.raises(ValueError, match="Accendi"):
        agent.wear(on_head=True)

    on = agent.power_on()
    assert on["power"] == "on"
    assert on["phase"] == "idle"
    assert agent.memory_path.is_file()

    worn = agent.wear(on_head=True)
    assert worn["wear"] == "on_head"
    assert worn["contact_ok"] is True
    assert worn["ready_for_impulses"] is True
    assert len(worn["contact_channels"]) == 8

    payload = agent.receive_impulse("ACCENDI")
    assert payload["impulse"]["kind"] == "ACCENDI"
    assert payload["impulse"]["intensity"] > 0
    assert payload["impulse"]["signal_source"] == "physionet_corpus"
    assert payload["impulse"]["features"]
    assert payload["impulse"]["window_stats"]["n_channels"] == 8
    assert payload["status"]["impulses_count"] == 1
    assert payload["status"]["corpus_available"] is True
    assert payload["window_shape"][0] == 8

    # Reload from disk — memory must persist for later steps.
    again = SimulatedHeadsetAgent(
        username="maria",
        headset_id="cuffia-sim-1",
        data_root=tmp_path,
        seed=99,
    )
    st = again.status()
    assert st["power"] == "on"
    assert st["wear"] == "on_head"
    assert st["contact_ok"] is True
    assert st["impulses_count"] == 1
    assert again.memory.impulses[0]["kind"] == "ACCENDI"


def test_si_no_replays_calibration_template(tmp_path: Path) -> None:
    """Second SI/NO reuses the calibrated impulse (same features + replay flag)."""

    agent = SimulatedHeadsetAgent(
        username="replay",
        headset_id="h-replay",
        data_root=tmp_path,
        seed=11,
    )
    agent.power_on()
    agent.wear(on_head=True)

    first = agent.receive_impulse("SI")
    assert first["replayed_from_calibration"] is False
    assert first["impulse"]["signal_source"] != "calibration_replay"
    assert first["impulse"]["features"]
    template_feats = list(first["impulse"]["features"])

    second = agent.receive_impulse("SI")
    assert second["replayed_from_calibration"] is True
    assert second["impulse"]["signal_source"] == "calibration_replay"
    assert second["impulse"]["replayed_from_calibration"] is True
    assert second["impulse"]["features"] == template_feats
    assert second["impulse"]["kind"] == "SI"
    assert second["status"]["impulses_count"] == 2
    # Live history grows with a new event (even if same second as template).
    assert len(agent.memory.impulses) == 2
    assert agent.memory.impulses[-1]["replayed_from_calibration"] is True

    # Alias YES also replays the SI template.
    third = agent.receive_impulse("YES")
    assert third["replayed_from_calibration"] is True
    assert third["impulse"]["features"] == template_feats

    # NO with no template yet still acquires a fresh window.
    no_first = agent.receive_impulse("NO")
    assert no_first["replayed_from_calibration"] is False
    assert "calibrazione" in (no_first.get("message") or "").lower()
    no_second = agent.receive_impulse("NO")
    assert no_second["replayed_from_calibration"] is True
    assert no_second["impulse"]["features"] == no_first["impulse"]["features"]


def test_agent_rejects_impulse_without_ready_state(tmp_path: Path) -> None:
    agent = SimulatedHeadsetAgent(
        username="luca",
        headset_id="h2",
        data_root=tmp_path,
        seed=7,
    )
    agent.power_on()
    with pytest.raises(ValueError, match="in testa"):
        agent.receive_impulse("ACCENDI")


def test_get_headset_agent_cache(tmp_path: Path) -> None:
    a = get_headset_agent(username="cache", headset_id="id-a", data_root=tmp_path)
    b = get_headset_agent(username="cache", headset_id="id-a", data_root=tmp_path)
    assert a is b
    c = get_headset_agent(username="cache", headset_id="id-b", data_root=tmp_path)
    assert c is not a
    assert c.headset_id == "id-b"


def _register_verified(client: TestClient, app, username: str = "maria") -> None:
    client.post(
        "/register",
        data={
            "username": username,
            "email": f"{username}@gmail.com",
            "password": "Segreta123",
        },
        follow_redirects=False,
    )
    profile = app.state.store.get(username)
    assert profile is not None
    profile.email_verified = True
    app.state.store.save(profile)
    client.post(
        "/anagrafica",
        data={
            "first_name": "Maria",
            "last_name": "Rossi",
            "gender": "female",
            "email": f"{username}@gmail.com",
            "phone_country": "IT",
            "phone_national": "3331234567",
            "phone_label": "iPhone",
        },
        follow_redirects=False,
    )


def test_web_headset_agent_apis(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "bci_iot.pipeline.headset_agent.brainflow_available",
        lambda: False,
    )
    monkeypatch.setattr(
        "bci_iot.pipeline.calibration_wizard.brainflow_available",
        lambda: False,
    )
    app = create_app(data_dir=tmp_path, session_secret="agent-secret")
    client = TestClient(app)
    _register_verified(client, app)

    page = client.get("/cuffia?stage=1")
    assert page.status_code == 200
    assert "Agente cuffia" in page.text
    assert "agent-power-on" in page.text
    assert "Vai alla calibrazione" in page.text
    stage2 = client.get("/cuffia?stage=2")
    assert stage2.status_code == 200
    assert "yn-si-btn" in stage2.text
    assert "yn-no-btn" in stage2.text

    power = client.post("/api/headset/power", json={"on": True})
    assert power.status_code == 200
    assert power.json()["agent"]["power"] == "on"

    wear = client.post("/api/headset/wear", json={"on_head": True})
    assert wear.status_code == 200
    body = wear.json()["agent"]
    assert body["wear"] == "on_head"
    assert body["contact_ok"] is True
    assert body["ready_for_impulses"] is True

    contact = client.post("/api/headset/contact", json={})
    assert contact.status_code == 200
    assert contact.json()["agent"]["contact_ok"] is True

    impulse = client.post("/api/headset/impulse", json={"kind": "ACCENDI"})
    assert impulse.status_code == 200
    data = impulse.json()
    assert data["impulse"]["kind"] == "ACCENDI"
    assert data["impulse"]["signal_source"] == "physionet_corpus"
    assert data["status"]["impulses_count"] >= 1

    mem = tmp_path / "headsets" / "maria" / "agent_memory.json"
    assert mem.is_file()

    agent_get = client.get("/api/headset/agent")
    assert agent_get.status_code == 200
    assert agent_get.json()["agent"]["impulses_count"] >= 1
    assert agent_get.json()["agent"]["corpus_available"] is True
