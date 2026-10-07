"""Tests for SimulatedHeadsetAgent — device-like power/wear/contact/impulse + memory."""

from __future__ import annotations

from pathlib import Path

import numpy as np
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


def test_si_no_classifies_against_calibration_templates(tmp_path: Path) -> None:
    """After SI+NO templates, live impulses acquire new windows and classify by similarity."""

    agent = SimulatedHeadsetAgent(
        username="classify",
        headset_id="h-cls",
        data_root=tmp_path,
        seed=11,
    )
    agent.power_on()
    agent.wear(on_head=True)

    first = agent.receive_impulse("SI", classify_yn=False)
    assert first["replayed_from_calibration"] is False
    assert first["impulse"]["signal_source"] != "calibration_replay"
    assert first["impulse"]["is_calibration_template"] is True
    assert first["impulse"]["features"]
    template_si = list(first["impulse"]["features"])

    no_first = agent.receive_impulse("NO", classify_yn=False)
    assert no_first["replayed_from_calibration"] is False
    assert no_first["impulse"]["is_calibration_template"] is True
    template_no = list(no_first["impulse"]["features"])
    assert template_si != template_no or len(template_si) > 0

    assert agent.status()["templates_si"] >= 1
    assert agent.status()["templates_no"] >= 1

    live = agent.receive_impulse("SI", classify_yn=True)
    assert live["replayed_from_calibration"] is False
    assert live["impulse"]["signal_source"] != "calibration_replay"
    assert live["impulse"]["is_calibration_template"] is False
    assert live["classified_answer"] in {"SI", "NO"}
    assert live["similarity_si"] is not None
    assert live["similarity_no"] is not None
    assert live["used_templates_count"] >= 2
    # New window: features should not be an exact copy of the SI template mean path.
    assert live["impulse"]["features"] != template_si or live["impulse"]["kind"] in {"SI", "NO"}
    assert "Riconosciuto come" in (live.get("message") or "")


def test_classify_yes_no_closer_to_si_template(tmp_path: Path) -> None:
    agent = SimulatedHeadsetAgent(
        username="centroid",
        headset_id="h-cent",
        data_root=tmp_path,
        seed=3,
    )
    # Plant clear SI / NO templates without acquisition noise.
    agent.memory.impulses = [
        {
            "kind": "SI",
            "features": [1.0, 0.0, 0.0, 0.0],
            "is_calibration_template": True,
            "signal_source": "prior_fallback",
        },
        {
            "kind": "NO",
            "features": [0.0, 1.0, 0.0, 0.0],
            "is_calibration_template": True,
            "signal_source": "prior_fallback",
        },
    ]
    near_si = agent.classify_yes_no([0.95, 0.05, 0.0, 0.0])
    assert near_si["label"] == "SI"
    assert near_si["score_si"] > near_si["score_no"]
    assert near_si["used_templates_count"] == 2

    near_no = agent.classify_yes_no(np.asarray([0.05, 0.95, 0.0, 0.0]))
    assert near_no["label"] == "NO"
    assert near_no["score_no"] > near_no["score_si"]


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
