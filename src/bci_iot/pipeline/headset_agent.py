"""Simulated headset agent — behaves like a physical device in your hands/on your head.

The agent:
- powers on/off
- is worn or removed (user confirms “on head”)
- estimates electrode contact quality
- receives mental *impulses* and yields EEG windows (BrainFlow synthetic or priors)
- persists memory so later steps remember pairing, contact, and captures
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import numpy as np

from bci_iot.accounts.names import safe_username
from bci_iot.acquisition.brainflow_source import (
    brainflow_available,
    capture_one_brainflow_window,
)
from bci_iot.acquisition.priors import COMMAND_PRIORS, synthesize_prior_window
from bci_iot.preprocessing.features import BandPowerExtractor
from bci_iot.types import EEGWindow

HeadsetPower = Literal["off", "on"]
WearState = Literal["off_head", "on_head"]
AgentPhase = Literal[
    "powered_off",
    "idle",
    "wearing",
    "contact_check",
    "ready",
    "receiving",
    "calibrating",
]

# UI / IoT action kinds → spectral prior command used to synthesize the impulse.
IMPULSE_KIND_ALIASES: dict[str, str] = {
    "NEXT_TRACK": "ACCENDI",
    "CAMBIA_CANZONE": "ACCENDI",
    "FOCUS": "ACCENDI",
    "PAUSE": "SPEGNI",
    "RELAX": "SPEGNI",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class ImpulseEvent:
    """One impulse the headset agent received and decoded into a window."""

    kind: str
    timestamp: str
    signal_source: str
    alpha: float
    beta: float
    intensity: float
    is_clean: bool
    contact_mean: float
    qc_flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HeadsetMemory:
    """Persistent memory of the virtual headset for one user."""

    username: str
    headset_id: str
    power: HeadsetPower = "off"
    wear: WearState = "off_head"
    phase: AgentPhase = "powered_off"
    contact_channels: list[float] = field(default_factory=list)
    contact_ok: bool = False
    impulses: list[dict[str, Any]] = field(default_factory=list)
    colour_counts: dict[str, int] = field(default_factory=dict)
    calibration_complete: bool = False
    last_impulse_at: str = ""
    updated_at: str = ""
    signal_path: str = "pending"  # brainflow_synthetic | prior_fallback

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HeadsetMemory:
        return cls(
            username=str(data.get("username") or ""),
            headset_id=str(data.get("headset_id") or ""),
            power=data.get("power") or "off",  # type: ignore[arg-type]
            wear=data.get("wear") or "off_head",  # type: ignore[arg-type]
            phase=data.get("phase") or "powered_off",  # type: ignore[arg-type]
            contact_channels=list(data.get("contact_channels") or []),
            contact_ok=bool(data.get("contact_ok")),
            impulses=list(data.get("impulses") or [])[-40:],
            colour_counts=dict(data.get("colour_counts") or {}),
            calibration_complete=bool(data.get("calibration_complete")),
            last_impulse_at=str(data.get("last_impulse_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
            signal_path=str(data.get("signal_path") or "pending"),
        )


class SimulatedHeadsetAgent:
    """Device-like agent: you configure it through wear/contact as if it were real."""

    def __init__(
        self,
        *,
        username: str,
        headset_id: str,
        data_root: Path | str,
        n_channels: int = 8,
        seed: int | None = None,
    ) -> None:
        self.username = username
        self.headset_id = headset_id
        self.data_root = Path(data_root)
        self.n_channels = n_channels
        self._rng = np.random.default_rng(seed if seed is not None else secrets_seed())
        self._extractor = BandPowerExtractor()
        self.memory = self._load_or_create()

    @property
    def memory_path(self) -> Path:
        folder = self.data_root / "headsets" / safe_username(self.username)
        folder.mkdir(parents=True, exist_ok=True)
        return folder / "agent_memory.json"

    def _load_or_create(self) -> HeadsetMemory:
        path = self.memory_path
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                mem = HeadsetMemory.from_dict(data)
                if self.headset_id and mem.headset_id != self.headset_id:
                    mem.headset_id = self.headset_id
                return mem
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                pass
        return HeadsetMemory(username=self.username, headset_id=self.headset_id)

    def save(self) -> Path:
        self.memory.updated_at = _utc_now()
        path = self.memory_path
        path.write_text(
            json.dumps(self.memory.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    def status(self) -> dict[str, Any]:
        mem = self.memory
        contact_mean = (
            float(np.mean(mem.contact_channels)) if mem.contact_channels else 0.0
        )
        return {
            "username": mem.username,
            "headset_id": mem.headset_id,
            "power": mem.power,
            "wear": mem.wear,
            "phase": mem.phase,
            "contact_ok": mem.contact_ok,
            "contact_mean": round(contact_mean, 3),
            "contact_channels": [round(float(x), 3) for x in mem.contact_channels],
            "signal_path": mem.signal_path,
            "brainflow_available": brainflow_available(),
            "impulses_count": len(mem.impulses),
            "last_impulse_at": mem.last_impulse_at,
            "colour_counts": dict(mem.colour_counts),
            "calibration_complete": mem.calibration_complete,
            "updated_at": mem.updated_at,
            "ready_for_impulses": mem.power == "on"
            and mem.wear == "on_head"
            and mem.contact_ok,
            "label": self._phase_label(),
            "detail": self._phase_detail(),
        }

    def _phase_label(self) -> str:
        mapping = {
            "powered_off": "Spenta",
            "idle": "Accesa — non in testa",
            "wearing": "In testa — contatto da verificare",
            "contact_check": "Controllo contatto",
            "ready": "Pronta — riceve impulsi",
            "receiving": "In ascolto",
            "calibrating": "In calibrazione",
        }
        return mapping.get(self.memory.phase, self.memory.phase)

    def _phase_detail(self) -> str:
        if self.memory.power == "off":
            return "Accendi la cuffia simulata come se l’avessi in mano."
        if self.memory.wear == "off_head":
            return "Indossala (conferma «in testa») per far partire il contatto elettrodi."
        if not self.memory.contact_ok:
            return "Contatto insufficiente: ripeti il controllo contatto."
        return (
            "La cuffia è in testa e ascolta. Gli impulsi arrivano come finestre EEG "
            "e restano in memoria per i passi successivi."
        )

    def power_on(self) -> dict[str, Any]:
        self.memory.power = "on"
        if self.memory.wear == "on_head" and self.memory.contact_ok:
            self.memory.phase = "ready"
        elif self.memory.wear == "on_head":
            self.memory.phase = "wearing"
        else:
            self.memory.phase = "idle"
        self.memory.signal_path = (
            "brainflow_synthetic" if brainflow_available() else "prior_fallback"
        )
        self.save()
        return self.status()

    def power_off(self) -> dict[str, Any]:
        self.memory.power = "off"
        self.memory.phase = "powered_off"
        self.save()
        return self.status()

    def wear(self, *, on_head: bool = True) -> dict[str, Any]:
        if self.memory.power != "on":
            raise ValueError("Accendi prima la cuffia.")
        self.memory.wear = "on_head" if on_head else "off_head"
        if not on_head:
            self.memory.contact_ok = False
            self.memory.contact_channels = []
            self.memory.phase = "idle"
        else:
            self.memory.phase = "wearing"
            # Auto first contact pass when worn (device-like).
            self.check_contact()
            return self.status()
        self.save()
        return self.status()

    def check_contact(self) -> dict[str, Any]:
        """Simulate per-channel contact/impedance; good enough when worn."""

        if self.memory.power != "on":
            raise ValueError("Accendi prima la cuffia.")
        if self.memory.wear != "on_head":
            raise ValueError("Indossa la cuffia (in testa) prima del contatto.")

        self.memory.phase = "contact_check"
        # Higher quality when on head; small random variation per channel.
        base = 0.82 + float(self._rng.uniform(-0.05, 0.08))
        channels = [
            float(np.clip(base + self._rng.normal(0, 0.04), 0.35, 0.99))
            for _ in range(self.n_channels)
        ]
        self.memory.contact_channels = channels
        mean = float(np.mean(channels))
        self.memory.contact_ok = mean >= 0.72 and min(channels) >= 0.55
        self.memory.phase = "ready" if self.memory.contact_ok else "wearing"
        self.save()
        status = self.status()
        status["contact_pass"] = self.memory.contact_ok
        return status

    def _acquire_window(
        self, impulse_kind: str, *, prefer_brainflow: bool = True
    ) -> tuple[EEGWindow, str]:
        kind = impulse_kind.strip().upper()
        kind = IMPULSE_KIND_ALIASES.get(kind, kind)
        # Map colour keys to prior commands when needed.
        from bci_iot.pipeline.calibration_wizard import COLOUR_TARGETS

        if kind in COLOUR_TARGETS:
            kind = COLOUR_TARGETS[kind].prior_command

        if prefer_brainflow and brainflow_available():
            try:
                # Blend: grab live BrainFlow noise floor, then overlay prior tones
                # so the impulse “arrives” on a live stream (device-like).
                live = capture_one_brainflow_window(
                    window_seconds=1.0, n_channels=self.n_channels
                )
                if kind in COMMAND_PRIORS:
                    prior = synthesize_prior_window(
                        kind,
                        sample_rate_hz=live.sample_rate_hz,
                        n_channels=self.n_channels,
                        window_seconds=1.0,
                        seed=int(self._rng.integers(0, 1_000_000)),
                    )
                    # Mix live board noise with intentional prior impulse.
                    mixed = 0.35 * live.data + 0.65 * prior.data
                    window = EEGWindow(
                        data=mixed.astype(np.float64),
                        sample_rate_hz=live.sample_rate_hz,
                        timestamp_s=time.perf_counter(),
                        channel_names=live.channel_names,
                    )
                    return window, "brainflow_impulse"
                return live, "brainflow_synthetic"
            except Exception:
                pass

        if kind not in COMMAND_PRIORS:
            kind = "ACCENDI"
        window = synthesize_prior_window(
            kind,
            n_channels=self.n_channels,
            seed=int(self._rng.integers(0, 1_000_000)),
        )
        return window, "prior_fallback"

    def receive_impulse(
        self,
        kind: str,
        *,
        colour_key: str | None = None,
        prefer_brainflow: bool = True,
    ) -> dict[str, Any]:
        """Headset receives a mental impulse and stores it in memory."""

        if self.memory.power != "on":
            raise ValueError("La cuffia è spenta.")
        if self.memory.wear != "on_head":
            raise ValueError("Indossa la cuffia in testa per ricevere impulsi.")
        if not self.memory.contact_ok:
            raise ValueError("Contatto elettrodi insufficiente: ripeti il controllo.")

        self.memory.phase = "receiving"
        window, source = self._acquire_window(
            kind, prefer_brainflow=prefer_brainflow
        )
        # Contact quality slightly modulates amplitude (poorer contact → weaker signal).
        contact_mean = float(np.mean(self.memory.contact_channels) or 0.8)
        window = EEGWindow(
            data=(window.data * (0.55 + 0.45 * contact_mean)).astype(np.float64),
            sample_rate_hz=window.sample_rate_hz,
            timestamp_s=window.timestamp_s,
            channel_names=window.channel_names,
        )
        features = self._extractor.transform(window)
        report = self._extractor.last_artifact_report
        alpha = float(features.values[0])
        beta = float(features.values[1])
        intensity = float(np.clip(50.0 + 18.0 * (beta - alpha), 5.0, 98.0))
        qc = list(report.flags) if report is not None else []

        event = ImpulseEvent(
            kind=kind.strip().upper(),
            timestamp=_utc_now(),
            signal_source=source,
            alpha=round(alpha, 4),
            beta=round(beta, 4),
            intensity=round(intensity, 1),
            is_clean=bool(features.is_clean),
            contact_mean=round(contact_mean, 3),
            qc_flags=qc,
        )
        self.memory.impulses.append(event.to_dict())
        self.memory.impulses = self.memory.impulses[-40:]
        self.memory.last_impulse_at = event.timestamp
        self.memory.signal_path = source
        if colour_key:
            key = colour_key.strip().upper()
            counts = dict(self.memory.colour_counts)
            counts[key] = int(counts.get(key) or 0) + 1
            self.memory.colour_counts = counts
        self.memory.phase = "ready"
        self.save()

        return {
            "impulse": event.to_dict(),
            "features": features.values.tolist(),
            "feature_names": list(features.names),
            "is_clean": bool(features.is_clean),
            "status": self.status(),
            "window_shape": list(window.data.shape),
        }

    def mark_calibration_complete(self) -> None:
        self.memory.calibration_complete = True
        self.memory.phase = "ready"
        self.save()

    def reset_session(self, *, keep_id: bool = True) -> dict[str, Any]:
        hid = self.memory.headset_id if keep_id else self.headset_id
        self.memory = HeadsetMemory(username=self.username, headset_id=hid)
        self.save()
        return self.status()


def secrets_seed() -> int:
    import secrets

    return secrets.randbelow(1_000_000_000)


_agents: dict[str, SimulatedHeadsetAgent] = {}


def get_headset_agent(
    *,
    username: str,
    headset_id: str,
    data_root: Path | str,
) -> SimulatedHeadsetAgent:
    """Process-local agent cache; memory is always reloaded from disk on miss."""

    key = safe_username(username)
    agent = _agents.get(key)
    root = Path(data_root)
    if (
        agent is None
        or agent.headset_id != headset_id
        or agent.data_root != root
    ):
        agent = SimulatedHeadsetAgent(
            username=username,
            headset_id=headset_id,
            data_root=root,
        )
        _agents[key] = agent
    return agent
