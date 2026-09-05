"""Abstract EEG source contract shared by simulator, file replay, and hardware."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any

from bci_iot.types import EEGWindow


class EEGSource(ABC):
    """Producer of fixed-length EEG windows.

    Hardware (future headset) and :class:`SyntheticEEGSource` implement the same
    interface so the rest of the pipeline stays unchanged.
    """

    @abstractmethod
    def start(self) -> None:
        """Open the device or stream."""

    @abstractmethod
    def stop(self) -> None:
        """Release resources."""

    @abstractmethod
    def iter_windows(self) -> Iterator[EEGWindow]:
        """Yield successive EEG windows until stopped or exhausted."""

    def __enter__(self) -> EEGSource:
        self.start()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.stop()
