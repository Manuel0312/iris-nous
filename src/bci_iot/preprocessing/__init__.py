"""Signal preprocessing and spectral feature extraction."""

from __future__ import annotations

from bci_iot.preprocessing.artifacts import ArtifactDetector, ArtifactReport
from bci_iot.preprocessing.features import BandPowerExtractor
from bci_iot.preprocessing.filters import bandpass_filter

__all__ = [
    "ArtifactDetector",
    "ArtifactReport",
    "BandPowerExtractor",
    "bandpass_filter",
]
