"""Simulated headset agent — pairing, contact, impulses, SI/NO classify."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from bci_iot.pipeline.headset_agent import SimulatedHeadsetAgent, get_headset_agent


def test_power_wear_contact_ready(tmp_path: Path) -> None:
    agent = SimulatedHeadsetAgent(
        username="alex",
        headset_id="h1",
        data_root=tmp_path,
        seed=1,
    )
    on = agent.power_on()
    assert on["phase"] == "idle"
    assert agent.memory.power == "on"
    wear = agent.wear(on_head=True)
    assert wear["wear"] == "on_head"
    contact = agent.check_contact()
    assert contact["contact_ok"] is True
    st = agent.status()
    assert st["ready_for_impulses"] is True


def test_impulse_persists_across_reload(tmp_path: Path) -> None:
    agent = SimulatedHeadsetAgent(
        username="maria",
        headset_id="h2",
        data_root=tmp_path,
        seed=7,
    )
    agent.power_on()
    agent.wear(on_head=True)
    agent.check_contact()
    out = agent.receive_impulse("ACCENDI", classify_yn=False)
    assert out["impulse"]["kind"] == "ACCENDI"
    again = SimulatedHeadsetAgent(
        username="maria",
        headset_id="h2",
        data_root=tmp_path,
        seed=7,
    )
    st = again.status()
    assert st["impulses_count"] == 1
    assert again.memory.impulses[0]["kind"] == "ACCENDI"


def test_si_no_classifies_against_calibration_templates(tmp_path: Path) -> None:
    """After SI+NO templates, live impulses are centroid+noise then classified."""

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
    assert live["impulse"]["signal_source"] == "template_plus_noise"
    assert live["impulse"]["is_calibration_template"] is False
    assert live["classified_answer"] == "SI"
    assert live["similarity_si"] is not None
    assert live["similarity_no"] is not None
    assert live["similarity_si"] >= live["similarity_no"]
    assert live["used_templates_count"] >= 2
    assert live["impulse"]["features"] != template_si
    assert "Riconosciuto come" in (live.get("message") or "")


def test_live_si_no_stable_with_seed(tmp_path: Path) -> None:
    """20× SI and 20× NO with fixed seed → always classified as the button."""

    agent = SimulatedHeadsetAgent(
        username="stable",
        headset_id="h-stable",
        data_root=tmp_path,
        seed=99,
    )
    agent.power_on()
    agent.wear(on_head=True)
    # Distinct planted centroids (avoid acquisition overlap).
    agent.memory.impulses = [
        {
            "kind": "SI",
            "features": [1.0, 0.05, 0.1, 0.0],
            "feature_names": ["a", "b", "c", "d"],
            "is_calibration_template": True,
            "signal_source": "prior_fallback",
            "alpha": 1.0,
            "beta": 0.05,
        },
        {
            "kind": "NO",
            "features": [0.05, 1.0, 0.0, 0.1],
            "feature_names": ["a", "b", "c", "d"],
            "is_calibration_template": True,
            "signal_source": "prior_fallback",
            "alpha": 0.05,
            "beta": 1.0,
        },
    ]
    si_centroid = [1.0, 0.05, 0.1, 0.0]
    for _ in range(20):
        out = agent.receive_impulse("SI", classify_yn=True)
        assert out["classified_answer"] == "SI"
        assert out["impulse"]["features"] != si_centroid
        assert out["impulse"]["signal_source"] == "template_plus_noise"
    no_centroid = [0.05, 1.0, 0.0, 0.1]
    for _ in range(20):
        out = agent.receive_impulse("NO", classify_yn=True)
        assert out["classified_answer"] == "NO"
        assert out["impulse"]["features"] != no_centroid
    # Templates must survive the live impulse ring buffer.
    assert agent.status()["templates_si"] >= 1
    assert agent.status()["templates_no"] >= 1


def test_live_yn_requires_both_templates(tmp_path: Path) -> None:
    agent = SimulatedHeadsetAgent(
        username="needboth",
        headset_id="h-need",
        data_root=tmp_path,
        seed=5,
    )
    agent.power_on()
    agent.wear(on_head=True)
    agent.receive_impulse("SI", classify_yn=False)
    with pytest.raises(ValueError, match="Calibra prima"):
        agent.receive_impulse("SI", classify_yn=True)


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
        headset_id="h3",
        data_root=tmp_path,
        seed=2,
    )
    with pytest.raises(ValueError, match="spenta"):
        agent.receive_impulse("SI")


def test_get_headset_agent_cached(tmp_path: Path) -> None:
    a = get_headset_agent(username="u1", headset_id="h", data_root=tmp_path)
    b = get_headset_agent(username="u1", headset_id="h", data_root=tmp_path)
    assert a is b
