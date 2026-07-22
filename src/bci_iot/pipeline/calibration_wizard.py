"""Interactive per-user calibration: colour / mental image → EEG features.

Voilà trains four macro colours (folders), not an open vocabulary of words.
Each colour reuses a literature spectral prior so the simulator stays coherent
until a real headset replaces ``synthesize_prior_window``.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from bci_iot.accounts.names import safe_username
from bci_iot.acquisition.priors import synthesize_prior_window
from bci_iot.ml.sklearn_classifier import SklearnIntentClassifier
from bci_iot.pipeline.macro_folders import FOLDER_META, FolderId
from bci_iot.preprocessing.features import BandPowerExtractor
from bci_iot.types import IntentLabel


@dataclass(frozen=True, slots=True)
class ColourTarget:
    """One calibratable mental colour / folder cue."""

    key: str  # ROSSO, VERDE, …
    folder: FolderId
    prior_command: str  # spectral prior to synthesize
    intent: IntentLabel
    image_cue: str


# Four colours ↔ four folders ↔ four intents (pipeline-compatible labels).
COLOUR_TARGETS: dict[str, ColourTarget] = {
    "ROSSO": ColourTarget(
        key="ROSSO",
        folder=FolderId.VIDEO,
        prior_command="ACCENDI",
        intent=IntentLabel.FOCUS,
        image_cue="Immagina il rosso: schermo video / YouTube",
    ),
    "VERDE": ColourTarget(
        key="VERDE",
        folder=FolderId.CHAT,
        prior_command="RISPONDI",
        intent=IntentLabel.ACCEPT,
        image_cue="Immagina il verde: bolla di chat / WhatsApp",
    ),
    "BLU": ColourTarget(
        key="BLU",
        folder=FolderId.SOCIAL,
        prior_command="RIFIUTA",
        intent=IntentLabel.REJECT,
        image_cue="Immagina il blu: feed social / Instagram",
    ),
    "GIALLO": ColourTarget(
        key="GIALLO",
        folder=FolderId.CASA,
        prior_command="SPEGNI",
        intent=IntentLabel.RELAX,
        image_cue="Immagina il giallo: casa / luci calde",
    ),
}

CALIBRATION_COLORS: tuple[str, ...] = tuple(COLOUR_TARGETS.keys())
# Back-compat alias used by older tests/imports
CALIBRATION_WORDS: tuple[str, ...] = CALIBRATION_COLORS
SAMPLES_PER_WORD = 3
SAMPLES_PER_COLOUR = SAMPLES_PER_WORD


def colour_targets_public() -> list[dict[str, Any]]:
    """JSON-serialisable list for the calibration UI."""

    out: list[dict[str, Any]] = []
    for key, target in COLOUR_TARGETS.items():
        meta = FOLDER_META[target.folder]
        out.append(
            {
                "key": key,
                "folder": target.folder.value,
                "label": meta["label"],
                "color": meta["color"],
                "color_name": meta["color_name"],
                "cue": target.image_cue,
                "intent": target.intent.value,
            }
        )
    return out


@dataclass
class CaptureResult:
    command: str
    intent: str
    intensity: float
    alpha: float
    beta: float
    samples_for_word: int
    needed_for_word: int
    progress: dict[str, int]
    complete_enough: bool
    folder: str = ""
    color_name: str = ""
    cue: str = ""


@dataclass
class CalibrationSession:
    """In-memory capture buffer for one logged-in user (colour imagery)."""

    username: str
    headset_id: str
    pairing_code: str
    seed: int = 11
    samples_per_word: int = SAMPLES_PER_COLOUR
    _rng: np.random.Generator = field(init=False, repr=False)
    _extractor: BandPowerExtractor = field(init=False, repr=False)
    _features: list[np.ndarray] = field(default_factory=list, repr=False)
    _labels: list[str] = field(default_factory=list, repr=False)
    _counts: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._rng = np.random.default_rng(self.seed)
        self._extractor = BandPowerExtractor(notch_hz=None)
        self._counts = {c: 0 for c in CALIBRATION_COLORS}

    def progress(self) -> dict[str, int]:
        return dict(self._counts)

    def complete_enough(self) -> bool:
        return all(self._counts[c] >= self.samples_per_word for c in CALIBRATION_COLORS)

    def capture(self, command: str) -> CaptureResult:
        key = command.strip().upper()
        # Accept folder id aliases too (video → ROSSO)
        aliases = {
            "VIDEO": "ROSSO",
            "CHAT": "VERDE",
            "SOCIAL": "BLU",
            "CASA": "GIALLO",
        }
        key = aliases.get(key, key)
        if key not in COLOUR_TARGETS:
            raise KeyError(f"Unknown colour: {command}")

        target = COLOUR_TARGETS[key]
        window = synthesize_prior_window(
            target.prior_command,
            seed=int(self._rng.integers(0, 1_000_000)),
        )
        features = self._extractor.transform(window)
        alpha = float(features.values[0])
        beta = float(features.values[1])
        intensity = float(np.clip(50.0 + 18.0 * (beta - alpha), 5.0, 98.0))

        intent = target.intent.value
        self._features.append(features.values.copy())
        self._labels.append(intent)
        self._counts[key] = self._counts.get(key, 0) + 1
        meta = FOLDER_META[target.folder]

        return CaptureResult(
            command=key,
            intent=intent,
            intensity=round(intensity, 1),
            alpha=round(alpha, 4),
            beta=round(beta, 4),
            samples_for_word=self._counts[key],
            needed_for_word=self.samples_per_word,
            progress=self.progress(),
            complete_enough=self.complete_enough(),
            folder=target.folder.value,
            color_name=meta["color_name"],
            cue=target.image_cue,
        )

    def finish(self, models_dir: Path | str = "models/users") -> tuple[Path, float]:
        if not self.complete_enough():
            raise ValueError("Calibrazione incompleta: registra tutti i colori.")
        if len(self._features) < 4:
            raise ValueError("Troppi pochi campioni.")

        x = np.vstack(self._features)
        y = np.array(self._labels, dtype=object)
        clf = SklearnIntentClassifier()
        clf.fit(x, y)
        accuracy = float(clf._model.score(x, y))

        out = Path(models_dir) / f"{safe_username(self.username)}.joblib"
        out.parent.mkdir(parents=True, exist_ok=True)
        clf.save(out)
        return out, accuracy


def new_pairing_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"
