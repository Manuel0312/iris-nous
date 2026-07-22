"""EEG acquisition abstractions and simulator-friendly sources."""

from __future__ import annotations

from bci_iot.acquisition.base import EEGSource
from bci_iot.acquisition.brainflow_source import BrainFlowSyntheticSource, brainflow_available
from bci_iot.acquisition.factory import create_eeg_source
from bci_iot.acquisition.priors import COMMAND_PRIORS, list_demo_commands, synthesize_prior_window
from bci_iot.acquisition.synthetic import SyntheticEEGSource

__all__ = [
    "BrainFlowSyntheticSource",
    "COMMAND_PRIORS",
    "EEGSource",
    "SyntheticEEGSource",
    "brainflow_available",
    "create_eeg_source",
    "list_demo_commands",
    "synthesize_prior_window",
]
