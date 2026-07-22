"""Local JSON profile store for account login and headset configuration."""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from bci_iot.accounts.gender import normalize_gender
from bci_iot.accounts.otp import (
    generate_otp_code,
    hash_otp,
    otp_expiry,
    otp_is_expired,
    otp_matches,
)
from bci_iot.accounts.phone_countries import format_phone_display, normalize_phone
from bci_iot.accounts.security import hash_password, password_strength, verify_password
from bci_iot.accounts.validators import normalize_email, validate_person_name


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


OtpPurpose = Literal["verify_email", "verify_phone", "recover"]


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
    email: str = ""
    phone_label: str = ""
    phone_country: str = ""
    phone_dial: str = ""
    phone_national: str = ""
    phone_e164: str = ""
    email_verified: bool = False
    phone_verified: bool = False
    otp_hash: str = ""
    otp_channel: str = ""
    otp_purpose: str = ""
    otp_expires_at: str = ""
    anagrafica_complete: bool = False
    calibration_complete: bool = False
    pairing_code: str = ""
    phone_paired: bool = False
    phone_last_seen_at: str = ""
    photo_filename: str = ""
    last_seen_at: str = ""
    deleted_at: str = ""
    # Spotify bridge (tokens never exposed via public_dict).
    spotify_access_token: str = ""
    spotify_refresh_token: str = ""
    spotify_token_expires_at: str = ""
    spotify_user_id: str = ""
    spotify_display_name: str = ""
    # Soft usage metrics for the private dashboard (demo-friendly).
    usage_stats: dict[str, Any] = field(default_factory=dict)

    @property
    def spotify_linked(self) -> bool:
        return bool(self.spotify_refresh_token or self.spotify_access_token)

    @property
    def phone_online(self) -> bool:
        if not self.phone_last_seen_at:
            return False
        try:
            seen = datetime.fromisoformat(self.phone_last_seen_at.replace("Z", "+00:00"))
            if seen.tzinfo is None:
                seen = seen.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) - seen <= timedelta(seconds=45)
        except ValueError:
            return False

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
    def phone_display(self) -> str:
        return format_phone_display(dial=self.phone_dial, national=self.phone_national)

    @property
    def account_verified(self) -> bool:
        return bool(self.email_verified or self.phone_verified)

    @property
    def verification_pending(self) -> bool:
        return not self.account_verified

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
        data.pop("spotify_access_token", None)
        data.pop("spotify_refresh_token", None)
        data.pop("otp_hash", None)
        data["spotify_linked"] = self.spotify_linked
        data["phone_online"] = self.phone_online
        data["phone_display"] = self.phone_display
        data["account_verified"] = self.account_verified
        data["verification_pending"] = self.verification_pending
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
            email=str(data.get("email") or ""),
            phone_label=str(data.get("phone_label") or ""),
            phone_country=str(data.get("phone_country") or ""),
            phone_dial=str(data.get("phone_dial") or ""),
            phone_national=str(data.get("phone_national") or ""),
            phone_e164=str(data.get("phone_e164") or ""),
            email_verified=bool(data.get("email_verified", False)),
            phone_verified=bool(data.get("phone_verified", False)),
            otp_hash=str(data.get("otp_hash") or ""),
            otp_channel=str(data.get("otp_channel") or ""),
            otp_purpose=str(data.get("otp_purpose") or ""),
            otp_expires_at=str(data.get("otp_expires_at") or ""),
            anagrafica_complete=bool(data.get("anagrafica_complete", False)),
            calibration_complete=bool(data.get("calibration_complete", False)),
            pairing_code=str(data.get("pairing_code") or ""),
            phone_paired=bool(data.get("phone_paired", False)),
            phone_last_seen_at=str(data.get("phone_last_seen_at") or ""),
            photo_filename=str(data.get("photo_filename") or ""),
            last_seen_at=str(data.get("last_seen_at") or ""),
            deleted_at=str(data.get("deleted_at") or ""),
            spotify_access_token=str(data.get("spotify_access_token") or ""),
            spotify_refresh_token=str(data.get("spotify_refresh_token") or ""),
            spotify_token_expires_at=str(data.get("spotify_token_expires_at") or ""),
            spotify_user_id=str(data.get("spotify_user_id") or ""),
            spotify_display_name=str(data.get("spotify_display_name") or ""),
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

    def find_by_email(self, email: str) -> UserProfile | None:
        try:
            needle = normalize_email(email)
        except ValueError:
            needle = (email or "").strip().casefold()
        if not needle:
            return None
        for profile in self.list_profiles():
            if profile.deleted_at:
                continue
            if profile.email.casefold() == needle:
                return profile
        return None

    def find_by_phone_e164(self, phone_e164: str) -> UserProfile | None:
        needle = (phone_e164 or "").strip()
        if not needle:
            return None
        for profile in self.list_profiles():
            if profile.deleted_at:
                continue
            if profile.phone_e164 == needle:
                return profile
        return None

    def find_by_identifier(self, identifier: str) -> UserProfile | None:
        """Resolve username, email, or phone (E.164 / national digits)."""
        raw = (identifier or "").strip()
        if not raw:
            return None
        by_user = self.get(raw)
        if by_user is not None and not by_user.deleted_at:
            return by_user
        if "@" in raw:
            found = self.find_by_email(raw)
            if found is not None:
                return found
        digits = "".join(ch for ch in raw if ch.isdigit())
        if raw.startswith("+") or len(digits) >= 8:
            e164 = raw if raw.startswith("+") else f"+{digits}"
            found = self.find_by_phone_e164(e164)
            if found is not None:
                return found
            # Fallback: match national part against stored phones
            for profile in self.list_profiles():
                if profile.deleted_at or not profile.phone_national:
                    continue
                if profile.phone_national == digits or profile.phone_e164.endswith(digits):
                    return profile
        return None

    def create_account(
        self,
        username: str,
        password: str,
        *,
        email: str = "",
        headset_id: str = "",
        notes: str = "",
        action_map: dict[str, str] | None = None,
        is_admin: bool = False,
    ) -> UserProfile:
        """Register a new account. Raises ``ValueError`` if username/email exists."""

        username = username.strip()
        if not username:
            raise ValueError("username must be non-empty")
        if is_admin:
            if len(password) < 6:
                raise ValueError("password must be at least 6 characters")
            email_norm = normalize_email(email) if email.strip() else f"{username}@iris.local"
        else:
            check = password_strength(password)
            if not check.ok:
                raise ValueError(check.message)
            email_norm = normalize_email(email)
        if self.exists(username):
            raise ValueError("Username già in uso. Scegline uno univoco.")
        if self.find_by_email(email_norm) is not None:
            raise ValueError(
                "Questa email è già registrata. Probabilmente hai già un account: "
                "usa «Password dimenticata?» con username, email o telefono."
            )

        profile = UserProfile(
            username=username,
            password_hash=hash_password(password),
            headset_id=headset_id.strip(),
            action_map=dict(action_map or {}),
            notes=notes,
            is_admin=bool(is_admin),
            email=email_norm,
            email_verified=bool(is_admin),
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
            if not existing.email:
                existing.email = f"{username}@iris.local"
                existing.email_verified = True
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
            email=f"{username}@iris.local",
            notes="Account amministratore (accessi e utenti).",
            is_admin=True,
        )

    def authenticate(self, username: str, password: str) -> UserProfile | None:
        profile = self.get(username)
        if profile is None or profile.deleted_at:
            # Allow login with email as identifier
            profile = self.find_by_email(username)
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

    def reset_password_by_identity(
        self,
        username: str,
        *,
        first_name: str,
        last_name: str,
        new_password: str,
    ) -> UserProfile:
        """Legacy reset via username + anagrafica names."""
        profile = self.get(username.strip())
        if profile is None or profile.deleted_at:
            raise ValueError("Account non trovato.")
        if not profile.anagrafica_complete:
            raise ValueError(
                "Anagrafica incompleta: non posso verificare l'identità. "
                "Contatta l'amministratore."
            )
        if first_name.strip().casefold() != profile.first_name.strip().casefold():
            raise ValueError("Dati non corrispondenti. Controlla nome e cognome.")
        if last_name.strip().casefold() != profile.last_name.strip().casefold():
            raise ValueError("Dati non corrispondenti. Controlla nome e cognome.")
        check = password_strength(new_password)
        if not check.ok:
            raise ValueError(check.message)
        profile.password_hash = hash_password(new_password)
        self.save(profile)
        return profile

    def issue_otp(
        self,
        username: str,
        *,
        channel: Literal["email", "phone"],
        purpose: OtpPurpose,
    ) -> tuple[UserProfile, str]:
        profile = self.get(username)
        if profile is None or profile.deleted_at:
            raise ValueError("Account non trovato.")
        if channel == "email":
            if not profile.email:
                raise ValueError("Nessuna email associata all'account.")
            destination_ok = True
        else:
            if not profile.phone_e164:
                raise ValueError("Nessun numero di telefono associato all'account.")
            destination_ok = True
        if not destination_ok:
            raise ValueError("Canale non disponibile.")
        code = generate_otp_code()
        profile.otp_hash = hash_otp(code, salt=profile.user_id)
        profile.otp_channel = channel
        profile.otp_purpose = purpose
        profile.otp_expires_at = otp_expiry(minutes=15)
        self.save(profile)
        return profile, code

    def consume_otp(
        self,
        username: str,
        *,
        code: str,
        purpose: OtpPurpose | None = None,
    ) -> UserProfile:
        profile = self.get(username)
        if profile is None or profile.deleted_at:
            raise ValueError("Account non trovato.")
        if not profile.otp_hash:
            raise ValueError("Nessun codice attivo. Richiedine uno nuovo.")
        if purpose and profile.otp_purpose != purpose:
            raise ValueError("Codice non valido per questa operazione.")
        if otp_is_expired(profile.otp_expires_at):
            raise ValueError("Codice scaduto. Richiedine uno nuovo.")
        if not otp_matches(code, stored_hash=profile.otp_hash, salt=profile.user_id):
            raise ValueError("Codice non corretto.")
        channel = profile.otp_channel
        otp_purpose = profile.otp_purpose
        profile.otp_hash = ""
        profile.otp_channel = ""
        profile.otp_purpose = ""
        profile.otp_expires_at = ""
        if otp_purpose == "verify_email" or (otp_purpose == "recover" and channel == "email"):
            profile.email_verified = True
        if otp_purpose == "verify_phone" or (otp_purpose == "recover" and channel == "phone"):
            profile.phone_verified = True
        self.save(profile)
        return profile

    def set_password(self, username: str, new_password: str) -> UserProfile:
        profile = self.get(username)
        if profile is None:
            raise KeyError(f"unknown user: {username}")
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
        email: str = "",
        phone_country: str = "",
        phone_national: str = "",
        phone_label: str = "",
    ) -> UserProfile:
        profile = self.get(username)
        if profile is None:
            raise KeyError(f"unknown user: {username}")

        first = validate_person_name(first_name, field_label="Il nome", required=True)
        last = validate_person_name(last_name, field_label="Il cognome", required=False)
        phone_label_clean = (phone_label or "").strip()
        if len(phone_label_clean) > 64:
            raise ValueError("Etichetta telefono troppo lunga.")

        email_raw = (email or "").strip() or profile.email
        email_norm = normalize_email(email_raw)
        other = self.find_by_email(email_norm)
        if other is not None and other.username.casefold() != profile.username.casefold():
            raise ValueError(
                "Questa email è già registrata. Usa «Password dimenticata?» "
                "se stai recuperando un account esistente."
            )

        country_iso = (phone_country or "").strip()
        national_raw = (phone_national or "").strip()
        if not country_iso or not national_raw:
            raise ValueError("Seleziona il prefisso e inserisci il numero di telefono.")
        country, digits, e164 = normalize_phone(
            country_iso=country_iso,
            national=national_raw,
        )
        conflict = self.find_by_phone_e164(e164)
        if conflict is not None and conflict.username.casefold() != profile.username.casefold():
            raise ValueError("Questo numero di telefono è già associato a un altro account.")
        if (
            profile.phone_e164
            and profile.phone_e164 != e164
            and profile.phone_verified
        ):
            profile.phone_verified = False
        profile.phone_country = country.iso
        profile.phone_dial = country.dial
        profile.phone_national = digits
        profile.phone_e164 = e164

        if profile.email and profile.email != email_norm and profile.email_verified:
            profile.email_verified = False

        gender_norm = normalize_gender(gender)
        profile.first_name = first
        profile.last_name = last
        profile.gender = gender_norm
        profile.email = email_norm
        profile.phone_label = phone_label_clean
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
        profile.phone_last_seen_at = _utc_now()
        self.save(profile)
        return profile

    def unpair_phone(self, username: str) -> UserProfile:
        from bci_iot.pipeline.calibration_wizard import new_pairing_code

        profile = self.get(username)
        if profile is None:
            raise KeyError(f"unknown user: {username}")
        profile.phone_paired = False
        profile.phone_last_seen_at = ""
        profile.pairing_code = new_pairing_code()
        self.save(profile)
        return profile

    def touch_phone(self, username: str) -> UserProfile:
        profile = self.get(username)
        if profile is None:
            raise KeyError(f"unknown user: {username}")
        profile.phone_last_seen_at = _utc_now()
        self.save(profile)
        return profile

    def set_spotify_tokens(
        self,
        username: str,
        *,
        access_token: str,
        refresh_token: str | None = None,
        expires_at: str = "",
        user_id: str = "",
        display_name: str = "",
    ) -> UserProfile:
        profile = self.get(username)
        if profile is None:
            raise KeyError(f"unknown user: {username}")
        profile.spotify_access_token = access_token.strip()
        if refresh_token is not None and refresh_token.strip():
            profile.spotify_refresh_token = refresh_token.strip()
        profile.spotify_token_expires_at = expires_at.strip()
        if user_id:
            profile.spotify_user_id = user_id.strip()
        if display_name:
            profile.spotify_display_name = display_name.strip()
        self.save(profile)
        return profile

    def clear_spotify(self, username: str) -> UserProfile:
        profile = self.get(username)
        if profile is None:
            raise KeyError(f"unknown user: {username}")
        profile.spotify_access_token = ""
        profile.spotify_refresh_token = ""
        profile.spotify_token_expires_at = ""
        profile.spotify_user_id = ""
        profile.spotify_display_name = ""
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
            email=str(extra.get("email") or ""),
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
