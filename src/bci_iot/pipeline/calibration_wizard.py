"""Interactive per-user calibration: colour / mental image → EEG features.

Product metaphor: four colours (folders). Scientific honesty: colours are cues;
the signal comes from BrainFlow SyntheticBoard when available (same API as a
real headset), otherwise literature spectral priors with an explicit fallback flag.
"""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import numpy as np

from bci_iot.accounts.names import safe_username
from bci_iot.acquisition.brainflow_source import (
    brainflow_available,
    capture_one_brainflow_window,
)
from bci_iot.acquisition.priors import synthesize_prior_window
from bci_iot.ml.sklearn_classifier import SklearnIntentClassifier
from bci_iot.pipeline.macro_folders import FOLDER_META, FolderId
from bci_iot.preprocessing.features import BandPowerExtractor
from bci_iot.types import IntentLabel

HeadsetMode = Literal["simulated", "disconnected", "real"]

HEADSET_MODES: tuple[HeadsetMode, ...] = ("simulated", "disconnected", "real")


@dataclass(frozen=True, slots=True)
class ColourTarget:
    """One calibratable mental colour / folder cue."""

    key: str  # ROSSO, VERDE, …
    folder: FolderId
    prior_command: str  # spectral prior (fallback / label mapping)
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


def normalize_headset_mode(value: str | None) -> HeadsetMode:
    raw = (value or "simulated").strip().lower()
    if raw in {"simulated", "sim", "brainflow", "bypass"}:
        return "simulated"
    if raw in {"disconnected", "none", "off", "non_collegata"}:
        return "disconnected"
    if raw in {"real", "reale", "physical", "hardware"}:
        return "real"
    return "simulated"


def headset_status_payload(
    *,
    mode: HeadsetMode,
    headset_id: str,
    hosted: bool = False,
) -> dict[str, Any]:
    """Public snapshot for Config cuffia UI."""

    from bci_iot.acquisition.brainflow_source import probe_brainflow_connection

    bf = brainflow_available()
    probe: dict[str, object] | None = None
    can_calibrate = False
    label = ""
    detail = ""

    if mode == "disconnected":
        label = "Non collegata"
        detail = "Scegli la cuffia simulata per continuare la calibrazione senza hardware."
        can_calibrate = False
    elif mode == "real":
        label = "Reale (prossimamente)"
        detail = (
            "Driver cuffia fisica non ancora collegato. Per ora usa la modalità simulata "
            "(stessa API BrainFlow)."
        )
        can_calibrate = False
    else:
        label = "Simulata (BrainFlow)"
        if bf:
            probe = probe_brainflow_connection()
            can_calibrate = bool(probe.get("ok"))
            detail = (
                "Bypass hardware: stream SyntheticBoard, stesso percorso di una cuffia reale."
                if can_calibrate
                else str(probe.get("detail") or "SyntheticBoard non raggiungibile")
            )
        else:
            detail = (
                "BrainFlow non installato: in calibrazione useremo i prior letterari "
                "(fallback esplicito)."
            )
            can_calibrate = True  # prior fallback still allows protocol

    return {
        "mode": mode,
        "label": label,
        "detail": detail,
        "headset_id": headset_id,
        "brainflow_available": bf,
        "can_calibrate": can_calibrate,
        "signal_source": (
            "brainflow_synthetic"
            if mode == "simulated" and bf
            else ("prior_fallback" if mode == "simulated" else mode)
        ),
        "hosted": hosted,
        "hosted_hint": (
            "Su Render Free la calibrazione completa è più stabile in locale "
            "(APRI IRIS locale)."
            if hosted
            else ""
        ),
        "probe": probe,
    }


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
    signal_source: str = "prior_fallback"
    is_clean: bool = True
    qc_flags: tuple[str, ...] = ()


@dataclass
class CalibrationSession:
    """In-memory capture buffer for one logged-in user (colour imagery)."""

    username: str
    headset_id: str
    pairing_code: str
    seed: int = 11
    samples_per_word: int = SAMPLES_PER_COLOUR
    headset_mode: HeadsetMode = "simulated"
    prefer_brainflow: bool = True
    data_root: Path | None = None
    _rng: np.random.Generator = field(init=False, repr=False)
    _extractor: BandPowerExtractor = field(init=False, repr=False)
    _features: list[np.ndarray] = field(default_factory=list, repr=False)
    _labels: list[str] = field(default_factory=list, repr=False)
    _meta: list[dict[str, Any]] = field(default_factory=list, repr=False)
    _counts: dict[str, int] = field(default_factory=dict)
    last_signal_source: str = "prior_fallback"

    def __post_init__(self) -> None:
        self._rng = np.random.default_rng(self.seed)
        self._extractor = BandPowerExtractor()
        self._counts = {c: 0 for c in CALIBRATION_COLORS}
        self.headset_mode = normalize_headset_mode(self.headset_mode)

    def progress(self) -> dict[str, int]:
        return dict(self._counts)

    def complete_enough(self) -> bool:
        return all(self._counts[c] >= self.samples_per_word for c in CALIBRATION_COLORS)

    def set_headset_mode(self, mode: str) -> HeadsetMode:
        self.headset_mode = normalize_headset_mode(mode)
        return self.headset_mode

    def _acquire_window(self, target: ColourTarget):
        """Prefer BrainFlow synthetic stream; fall back to literature prior."""

        if (
            self.prefer_brainflow
            and self.headset_mode == "simulated"
            and brainflow_available()
        ):
            try:
                window = capture_one_brainflow_window(window_seconds=1.0, n_channels=8)
                self.last_signal_source = "brainflow_synthetic"
                return window
            except Exception:
                pass

        window = synthesize_prior_window(
            target.prior_command,
            seed=int(self._rng.integers(0, 1_000_000)),
        )
        self.last_signal_source = "prior_fallback"
        return window

    def capture(self, command: str) -> CaptureResult:
        if self.headset_mode == "disconnected":
            raise ValueError(
                "Cuffia non collegata: in Configura seleziona la modalità simulata."
            )
        if self.headset_mode == "real":
            raise ValueError(
                "Cuffia reale non ancora supportata: usa la modalità simulata (BrainFlow)."
            )

        key = command.strip().upper()
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
        agent_payload: dict[str, Any] | None = None
        if self.headset_mode == "simulated" and self.data_root is not None:
            try:
                from bci_iot.pipeline.headset_agent import get_headset_agent

                agent = get_headset_agent(
                    username=self.username,
                    headset_id=self.headset_id,
                    data_root=self.data_root,
                )
                # Ensure device is ready as if on your head.
                if agent.memory.power != "on":
                    agent.power_on()
                if agent.memory.wear != "on_head":
                    agent.wear(on_head=True)
                if not agent.memory.contact_ok:
                    agent.check_contact()
                agent.memory.phase = "calibrating"
                agent.save()
                agent_payload = agent.receive_impulse(
                    target.prior_command,
                    colour_key=key,
                    prefer_brainflow=self.prefer_brainflow,
                )
                self.last_signal_source = str(
                    agent_payload["impulse"]["signal_source"]
                )
                features_arr = np.asarray(agent_payload["features"], dtype=np.float64)
                alpha = float(agent_payload["impulse"]["alpha"])
                beta = float(agent_payload["impulse"]["beta"])
                intensity = float(agent_payload["impulse"]["intensity"])
                is_clean = bool(agent_payload["is_clean"])
                qc_flags = tuple(agent_payload["impulse"].get("qc_flags") or ())
            except Exception:
                agent_payload = None

        if agent_payload is None:
            window = self._acquire_window(target)
            features = self._extractor.transform(window)
            report = self._extractor.last_artifact_report
            alpha = float(features.values[0])
            beta = float(features.values[1])
            intensity = float(np.clip(50.0 + 18.0 * (beta - alpha), 5.0, 98.0))
            qc_flags = tuple(report.flags) if report is not None else ()
            features_arr = features.values.copy()
            is_clean = bool(features.is_clean)

        intent = target.intent.value
        self._features.append(features_arr.copy())
        self._labels.append(intent)
        self._meta.append(
            {
                "colour": key,
                "intent": intent,
                "folder": target.folder.value,
                "signal_source": self.last_signal_source,
                "is_clean": is_clean,
                "qc_flags": list(qc_flags),
                "alpha": alpha,
                "beta": beta,
                "via_agent": agent_payload is not None,
                "captured_at": datetime.now(timezone.utc)
                .replace(microsecond=0)
                .isoformat(),
            }
        )
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
            signal_source=self.last_signal_source,
            is_clean=is_clean,
            qc_flags=qc_flags,
        )

    def _honest_accuracy(self, clf: SklearnIntentClassifier, x: np.ndarray, y: np.ndarray) -> float:
        """Holdout or leave-one-out estimate — never train-set score alone."""

        from bci_iot.types import FeatureVector

        n = len(y)
        if n < 4:
            return float(clf._model.score(x, y))

        def _score_indices(train_idx: list[int], test_idx: list[int]) -> float:
            fold = SklearnIntentClassifier()
            fold.fit(x[train_idx], y[train_idx])
            hits = 0
            for i in test_idx:
                fv = FeatureVector(
                    values=x[i],
                    names=("alpha_logpower", "beta_logpower", "alpha_beta_ratio"),
                    timestamp_s=0.0,
                    is_clean=True,
                )
                pred = fold.predict(fv)
                if pred.label.value == y[i]:
                    hits += 1
            return hits / max(1, len(test_idx))

        labels = list(dict.fromkeys(y.tolist()))
        test_idx: list[int] = []
        for lab in labels:
            idxs = [i for i, yy in enumerate(y) if yy == lab]
            if idxs:
                test_idx.append(idxs[-1])
        test_idx = sorted(set(test_idx))
        train_idx = [i for i in range(n) if i not in test_idx]
        if len(train_idx) >= 4 and len(test_idx) >= 2:
            return float(_score_indices(train_idx, test_idx))

        scores = [
            _score_indices([j for j in range(n) if j != i], [i]) for i in range(n)
        ]
        return float(np.mean(scores)) if scores else 0.0

    def finish(
        self,
        models_dir: Path | str = "models/users",
        *,
        samples_dir: Path | str | None = None,
    ) -> tuple[Path, float]:
        if not self.complete_enough():
            raise ValueError("Calibrazione incompleta: registra tutti i colori.")
        if len(self._features) < 4:
            raise ValueError("Troppi pochi campioni.")

        x = np.vstack(self._features)
        y = np.array(self._labels, dtype=object)
        clf = SklearnIntentClassifier()
        clf.fit(x, y)
        accuracy = self._honest_accuracy(clf, x, y)

        out = Path(models_dir) / f"{safe_username(self.username)}.joblib"
        out.parent.mkdir(parents=True, exist_ok=True)
        clf.save(out)

        root = Path(samples_dir) if samples_dir else self.data_root
        if root is not None:
            self._persist_samples(root, model_path=out, accuracy=accuracy)
            try:
                from bci_iot.pipeline.headset_agent import get_headset_agent

                agent = get_headset_agent(
                    username=self.username,
                    headset_id=self.headset_id,
                    data_root=root,
                )
                agent.mark_calibration_complete()
            except Exception:
                pass

        return out, accuracy

    def _persist_samples(
        self, data_root: Path, *, model_path: Path, accuracy: float
    ) -> Path:
        folder = Path(data_root) / "calibration" / safe_username(self.username)
        folder.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        payload = {
            "username": self.username,
            "headset_id": self.headset_id,
            "headset_mode": self.headset_mode,
            "accuracy_holdout": accuracy,
            "model_path": str(model_path),
            "saved_at": stamp,
            "samples": self._meta,
            "features": [row.tolist() for row in self._features],
            "labels": list(self._labels),
        }
        path = folder / f"session_{stamp}.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        latest = folder / "latest.json"
        latest.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        return path


def new_pairing_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"
