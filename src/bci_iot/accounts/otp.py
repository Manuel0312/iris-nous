"""One-time codes for email/phone verification and password recovery."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

# Avoid ambiguous characters (0/O, 1/I/L).
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


OTP_LENGTH = 6
OTP_MAX_ATTEMPTS = 5
OTP_COOLDOWN_SECONDS = 60
OTP_TTL_MINUTES = 10


def generate_otp_code(*, length: int = OTP_LENGTH) -> str:
    """6-character alphanumeric code (uppercase letters + digits, no spaces)."""
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


def normalize_otp(code: str) -> str:
    """Uppercase alphanumerics only — strips spaces and punctuation."""
    return "".join(ch for ch in (code or "").strip().upper() if ch.isalnum())


def otp_binding_salt(*, user_id: str, purpose: str, channel: str) -> str:
    """Bind the code to one account + purpose + channel (anti reuse / theft)."""
    return f"{user_id}|{purpose}|{channel}"


def hash_otp(code: str, *, salt: str) -> str:
    payload = f"{salt}:{normalize_otp(code)}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def otp_matches(code: str, *, stored_hash: str, salt: str) -> bool:
    if not stored_hash or not code:
        return False
    normalized = normalize_otp(code)
    if len(normalized) != OTP_LENGTH:
        return False
    digest = hash_otp(normalized, salt=salt)
    return hmac.compare_digest(digest, stored_hash)


def otp_expiry(*, minutes: int = OTP_TTL_MINUTES) -> str:
    return (_utc_now() + timedelta(minutes=minutes)).replace(microsecond=0).isoformat()


def otp_is_expired(expires_at: str) -> bool:
    if not expires_at:
        return True
    try:
        when = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
    except ValueError:
        return True
    return _utc_now() > when
