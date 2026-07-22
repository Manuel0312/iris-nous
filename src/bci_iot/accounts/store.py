"""Local JSON profile store for account login and headset configuration."""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from bci_iot.accounts.gender import normalize_gender
from bci_iot.accounts.security import hash_password, password_strength, verify_password


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(slots=True)
class UserProfile:
    """Personal account + headset configuration (local / free use)."""

    username: str
    password_hash: str
    headset_id: str = ""
    user_id: str = field(default_factory=lambda: str(uuid4()))
    action_map: dict[str, str] = field(default_factory=dict)
    notes: str = ""
    is_admin: bool = False
    first_name: str = ""
    last_name: str = ""
    gender: str = ""
    phone_label: str = ""
    anagrafica_complete: bool = False
    calibration_complete: bool = False
    pairing_code: str = ""
    phone_paired: bool = False
    photo_filename: str = ""
    last_seen_at: str = ""
    deleted_at: str = ""
    # Soft usage metrics for the private dashboard (demo-friendly).
    usage_stats: dict[str, Any] = field(default_factory=dict)

    @property
    def needs_anagrafica(self) -> bool:
        return not self.anagrafica_complete

    @property
    def needs_calibration(self) -> bool:
        return self.anagrafica_complete and not self.calibration_complete

    @property
    def display_name(self) -> str:
        parts = [self.first_name.strip(), self.last_name.strip()]
        name = " ".join(p for p in parts if p)
        return name or self.username

    @property
    def is_online(self) -> bool:
        if not self.last_seen_at:
            return False
        try:
            seen = datetime.fromisoformat(self.last_seen_at.replace("Z", "+00:00"))
            if seen.tzinfo is None:
                seen = seen.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) - seen <= timedelta(minutes=5)
        except ValueError:
            return False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def public_dict(self) -> dict[str, Any]:
        data = self.to_dict()
        data.pop("password_hash", None)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserProfile:
        password_hash = data.get("password_hash")
        if not password_hash:
            raise ValueError("profile is missing password_hash; re-register the account")
        return cls(
            username=str(data["username"]),
            password_hash=str(password_hash),
            headset_id=str(data.get("headset_id") or ""),
            user_id=str(data.get("user_id", uuid4())),
            action_map=dict(data.get("action_map") or {}),
            notes=str(data.get("notes") or ""),
            is_admin=bool(data.get("is_admin", False)),
            first_name=str(data.get("first_name") or ""),
            last_name=str(data.get("last_name") or ""),
            gender=str(data.get("gender") or ""),
            phone_label=str(data.get("phone_label") or ""),
            anagrafica_complete=bool(data.get("anagrafica_complete", False)),
            calibration_complete=bool(data.get("calibration_complete", False)),
            pairing_code=str(data.get("pairing_code") or ""),
            phone_paired=bool(data.get("phone_paired", False)),
            photo_filename=str(data.get("photo_filename") or ""),
            last_seen_at=str(data.get("last_seen_at") or ""),
            deleted_at=str(data.get("deleted_at") or ""),
            usage_stats=dict(data.get("usage_stats") or {}),
        )


class ProfileStore:
    """Persist user accounts as JSON files under ``data_dir``."""

    def __init__(self, data_dir: Path | str) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.deleted_dir = self.data_dir.parent / "profiles_deleted"
        self.photos_dir = self.data_dir.parent / "photos"
        self.photos_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, username: str) -> Path:
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in username.lower())
        return self.data_dir / f"{safe}.json"

    def exists(self, username: str) -> bool:
        return self._path_for(username).exists()

    def save(self, profile: UserProfile) -> None:
        path = self._path_for(profile.username)
        path.write_text(json.dumps(profile.to_dict(), indent=2), encoding="utf-8")

    def create_account(
        self,
        username: str,
        password: str,
        *,
        headset_id: str = "",
        notes: str = "",
        action_map: dict[str, str] | None = None,
        is_admin: bool = False,
    ) -> UserProfile:
        """Register a new account. Raises ``ValueError`` if the username exists."""

        username = username.strip()
        if not username:
            raise ValueError("username must be non-empty")
        if is_admin:
            if len(password) < 6:
                raise ValueError("password must be at least 6 characters")
        else:
            check = password_strength(password)
            if not check.ok:
                raise ValueError(check.message)
        if self.exists(username):
            raise ValueError("Username già in uso. Scegline uno univoco.")

        profile = UserProfile(
            username=username,
            password_hash=hash_password(password),
            headset_id=headset_id.strip(),
            action_map=dict(action_map or {}),
            notes=notes,
            is_admin=bool(is_admin),
            anagrafica_complete=bool(is_admin),
            calibration_complete=bool(is_admin),
            first_name="Admin" if is_admin else "",
            last_name="" if is_admin else "",
            gender="non_binary" if is_admin else "",
            pairing_code="" if not is_admin else "000000",
            phone_paired=bool(is_admin),
            usage_stats={
                "intents_fired": 0,
                "sessions": 0,
                "minutes_active": 0,
                "alpha_avg": 0.42,
                "beta_avg": 0.38,
                "last_activity": "",
            },
        )
        self.save(profile)
        return profile

    def ensure_admin(self, username: str, password: str) -> UserProfile:
        username = username.strip()
        existing = self.get(username)
        if existing is not None:
            changed = False
            if not existing.is_admin:
                existing.is_admin = True
                changed = True
            if not existing.anagrafica_complete:
                existing.anagrafica_complete = True
                existing.first_name = existing.first_name or "Admin"
                existing.gender = existing.gender or "non_binary"
                changed = True
            if not existing.calibration_complete:
                existing.calibration_complete = True
                existing.phone_paired = True
                existing.pairing_code = existing.pairing_code or "000000"
                changed = True
            if changed:
                self.save(existing)
            return existing
        return self.create_account(
            username,
            password,
            notes="Account amministratore (accessi e utenti).",
            is_admin=True,
        )

    def authenticate(self, username: str, password: str) -> UserProfile | None:
        profile = self.get(username)
        if profile is None or profile.deleted_at:
            return None
        if not verify_password(password, profile.password_hash):
            return None
        return profile

    def username_exists_active(self, username: str) -> bool:
        profile = self.get(username)
        return profile is not None and not profile.deleted_at

    def change_password(
        self,
        username: str,
        *,
        current_password: str,
        new_password: str,
    ) -> UserProfile:
        profile = self.get(username)
        if profile is None:
            raise KeyError(f"unknown user: {username}")
        if not verify_password(current_password, profile.password_hash):
            raise ValueError("Password non corretta")
        check = password_strength(new_password)
        if not check.ok:
            raise ValueError(check.message)
        profile.password_hash = hash_password(new_password)
        self.save(profile)
        return profile

    def touch_last_seen(self, username: str) -> None:
        profile = self.get(username)
        if profile is None:
            return
        profile.last_seen_at = _utc_now()
        self.save(profile)

    def set_photo(self, username: str, filename: str) -> UserProfile:
        profile = self.get(username)
        if profile is None:
            raise KeyError(f"unknown user: {username}")
        profile.photo_filename = filename
        self.save(profile)
        return profile

    def soft_delete(self, username: str) -> None:
        profile = self.get(username)
        if profile is None:
            raise KeyError(f"unknown user: {username}")
        if profile.is_admin:
            raise ValueError("Non puoi eliminare l'account amministratore.")
        profile.deleted_at = _utc_now()
        self.deleted_dir.mkdir(parents=True, exist_ok=True)
        dest = self.deleted_dir / self._path_for(username).name
        self.save(profile)
        shutil.move(str(self._path_for(username)), str(dest))

    def update_anagrafica(
        self,
        username: str,
        *,
        first_name: str,
        last_name: str,
        gender: str,
        phone_label: str = "",
    ) -> UserProfile:
        profile = self.get(username)
        if profile is None:
            raise KeyError(f"unknown user: {username}")

        first = first_name.strip()
        last = last_name.strip()
        phone = phone_label.strip()
        if not first:
            raise ValueError("Il nome è obbligatorio.")
        if len(first) > 64 or len(last) > 64:
            raise ValueError("Nome o cognome troppo lunghi.")
        if len(phone) > 64:
            raise ValueError("Etichetta telefono troppo lunga.")
        gender_norm = normalize_gender(gender)

        profile.first_name = first
        profile.last_name = last
        profile.gender = gender_norm
        profile.phone_label = phone
        profile.anagrafica_complete = True
        self.save(profile)
        return profile

    def ensure_headset_pairing(
        self,
        username: str,
        *,
        headset_id: str | None = None,
    ) -> UserProfile:
        from bci_iot.pipeline.calibration_wizard import new_pairing_code

        profile = self.get(username)
        if profile is None:
            raise KeyError(f"unknown user: {username}")
        changed = False
        if headset_id is not None and headset_id.strip():
            profile.headset_id = headset_id.strip()
            changed = True
        elif not profile.headset_id:
            profile.headset_id = f"cuffia-{profile.user_id[:8]}"
            changed = True
        if not profile.pairing_code:
            profile.pairing_code = new_pairing_code()
            changed = True
        if changed:
            self.save(profile)
        return profile

    def mark_calibration_complete(self, username: str) -> UserProfile:
        profile = self.get(username)
        if profile is None:
            raise KeyError(f"unknown user: {username}")
        profile.calibration_complete = True
        stats = dict(profile.usage_stats or {})
        stats["sessions"] = int(stats.get("sessions") or 0) + 1
        stats["last_activity"] = _utc_now()
        profile.usage_stats = stats
        self.save(profile)
        return profile

    def confirm_phone_pairing(self, username: str, code: str) -> UserProfile:
        profile = self.get(username)
        if profile is None:
            raise KeyError(f"unknown user: {username}")
        if not profile.pairing_code or code.strip() != profile.pairing_code:
            raise ValueError("Codice di associazione non valido.")
        profile.phone_paired = True
        self.save(profile)
        return profile

    def update_config(
        self,
        username: str,
        *,
        headset_id: str | None = None,
        notes: str | None = None,
        action_map: dict[str, str] | None = None,
    ) -> UserProfile:
        profile = self.get(username)
        if profile is None:
            raise KeyError(f"unknown user: {username}")
        if headset_id is not None:
            profile.headset_id = headset_id.strip()
        if notes is not None:
            profile.notes = notes
        if action_map is not None:
            profile.action_map = dict(action_map)
        self.save(profile)
        return profile

    def bump_usage(self, username: str, *, intent: str = "") -> None:
        profile = self.get(username)
        if profile is None:
            return
        stats = dict(profile.usage_stats or {})
        stats["intents_fired"] = int(stats.get("intents_fired") or 0) + 1
        stats["minutes_active"] = int(stats.get("minutes_active") or 0) + 1
        if intent:
            stats["last_intent"] = intent
        stats["last_activity"] = _utc_now()
        # Soft spectral demo averages
        alpha = float(stats.get("alpha_avg") or 0.4)
        beta = float(stats.get("beta_avg") or 0.4)
        stats["alpha_avg"] = round(min(0.95, max(0.05, alpha + 0.01)), 3)
        stats["beta_avg"] = round(min(0.95, max(0.05, beta + 0.008)), 3)
        profile.usage_stats = stats
        self.save(profile)

    def register(self, username: str, headset_id: str, **extra: Any) -> UserProfile:
        password = str(extra.get("password") or "")
        return self.create_account(
            username,
            password,
            headset_id=headset_id,
            notes=str(extra.get("notes") or ""),
            action_map=dict(extra.get("action_map") or {}),
        )

    def get(self, username: str) -> UserProfile | None:
        path = self._path_for(username)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return UserProfile.from_dict(data)

    def list_usernames(self) -> list[str]:
        return sorted(p.stem for p in self.data_dir.glob("*.json"))

    def list_profiles(self) -> list[UserProfile]:
        out: list[UserProfile] = []
        for name in self.list_usernames():
            # stem may differ from username casing — load via file
            path = self.data_dir / f"{name}.json"
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                out.append(UserProfile.from_dict(data))
            except (OSError, ValueError, KeyError):
                continue
        return out

    def count_online(self) -> int:
        return sum(1 for p in self.list_profiles() if p.is_online and not p.is_admin)

    def count_registered(self) -> int:
        return sum(1 for p in self.list_profiles() if not p.is_admin)

    def count_deleted(self) -> int:
        if not self.deleted_dir.exists():
            return 0
        return len(list(self.deleted_dir.glob("*.json")))
