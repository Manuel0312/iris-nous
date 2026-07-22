"""Tests for literature priors and impulse demo engine."""

from __future__ import annotations

from bci_iot.acquisition.priors import COMMAND_PRIORS, synthesize_prior_window
from bci_iot.pipeline.impulse_demo import ImpulseDemoEngine
from bci_iot.types import IntentLabel


def test_synthesize_spegni_has_expected_shape() -> None:
    window = synthesize_prior_window("SPEGNI", seed=1)
    assert window.data.shape == (8, 250)


def test_impulse_demo_accendi_and_spegni() -> None:
    engine = ImpulseDemoEngine(seed=5)
    on = engine.fire("ACCENDI")
    off = engine.fire("SPEGNI")
    assert on["command"] == "ACCENDI"
    assert off["command"] == "SPEGNI"
    assert on["action"] is not None
    assert off["action"] is not None
    assert "turn_on" in on["action"]["name"] or on["classified_intent"] == IntentLabel.FOCUS.value
    assert "turn_off" in off["action"]["name"] or off["classified_intent"] == IntentLabel.RELAX.value


def test_impulse_demo_rispondi_phone_action() -> None:
    engine = ImpulseDemoEngine(seed=9)
    result = engine.fire("RISPONDI")
    assert result["expected_intent"] == IntentLabel.ACCEPT.value
    assert result["classified_intent"] == IntentLabel.ACCEPT.value
    assert result["action"] is not None
    assert result["action"]["name"] == "phone.accept_call"


def test_all_commands_defined() -> None:
    assert set(COMMAND_PRIORS) >= {"ACCENDI", "SPEGNI", "RISPONDI", "RIFIUTA"}
