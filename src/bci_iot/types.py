"""Shared domain types used across pipeline modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np
from numpy.typing import NDArray


class IntentLabel(str, Enum):
    """Discrete neural intents produced by the ML engine."""

    IDLE = "IDLE"
    RELAX = "RELAX"
    FOCUS = "FOCUS"
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"


class ActionContext(str, Enum):
    """FSM context that remaps the same intent to different actions."""

    IDLE = "idle"
    LIGHT_MODE = "light_mode"
    MUSIC_MODE = "music_mode"
    CALL_MODE = "call_mode"


@dataclass(frozen=True, slots=True)
class EEGWindow:
    """A short multi-channel EEG segment ready for preprocessing."""

    data: NDArray[np.floating[Any]]
    sample_rate_hz: float
    timestamp_s: float
    channel_names: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.data.ndim != 2:
            raise ValueError("EEGWindow.data must have shape (n_channels, n_samples)")
        if self.sample_rate_hz <= 0:
            raise ValueError("sample_rate_hz must be positive")


@dataclass(frozen=True, slots=True)
class FeatureVector:
    """Numeric features extracted from one EEG window (e.g. α/β power)."""

    values: NDArray[np.floating[Any]]
    names: tuple[str, ...]
    timestamp_s: float
    is_clean: bool = True
    artifact_flags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.values.ndim != 1:
            raise ValueError("FeatureVector.values must be 1-D")
        if len(self.names) != self.values.shape[0]:
            raise ValueError("Feature names length must match values length")


@dataclass(frozen=True, slots=True)
class ClassifiedIntent:
    """Classifier output with confidence for the intent router."""

    label: IntentLabel
    confidence: float
    timestamp_s: float
    raw_scores: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be in [0, 1]")


@dataclass(frozen=True, slots=True)
class ActionCommand:
    """Typed command emitted by the FSM toward an integration client."""

    name: str
    target: str
    payload: dict[str, Any] = field(default_factory=dict)
    dry_run: bool = True
