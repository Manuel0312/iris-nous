"""Factory for EEG sources selected by configuration."""

from __future__ import annotations

from bci_iot.acquisition.base import EEGSource
from bci_iot.acquisition.brainflow_source import BrainFlowSyntheticSource, brainflow_available
from bci_iot.acquisition.synthetic import SyntheticEEGSource
from bci_iot.config import AcquisitionSettings


def create_eeg_source(
    settings: AcquisitionSettings,
    *,
    max_windows: int | None = None,
    seed: int = 42,
) -> EEGSource:
    """Create an :class:`EEGSource` from ``settings.source``.

    Supported values:
    - ``synthetic``: lightweight NumPy simulator (always available)
    - ``brainflow_synthetic``: BrainFlow SyntheticBoard (requires ``brainflow``)
    """

    name = settings.source.strip().lower()
    if name in {"synthetic", "numpy", "local"}:
        return SyntheticEEGSource(
            sample_rate_hz=settings.sample_rate_hz,
            n_channels=settings.n_channels,
            window_seconds=settings.window_seconds,
            max_windows=max_windows,
            seed=seed,
        )

    if name in {"brainflow_synthetic", "brainflow", "synthetic_board"}:
        if not brainflow_available():
            raise ImportError(
                "acquisition.source=brainflow_synthetic requires brainflow. "
                'Install with: pip install -e ".[acquisition]"'
            )
        return BrainFlowSyntheticSource(
            window_seconds=settings.window_seconds,
            n_channels=settings.n_channels,
            max_windows=max_windows,
        )

    raise ValueError(
        f"Unknown acquisition.source={settings.source!r}. "
        "Use 'synthetic' or 'brainflow_synthetic'."
    )
