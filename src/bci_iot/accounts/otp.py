"""One-time codes for email/phone verification and password recovery."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def generate_otp_code(*, digits: int = 6) -> str:
    upper = 10**digits
    return f"{secrets.randbelow(upper):0{digits}d}"


def hash_otp(code: str, *, salt: str) -> str:
    payload = f"{salt}:{code.strip()}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def otp_matches(code: str, *, stored_hash: str, salt: str) -> bool:
    if not stored_hash or not code:
        return False
    digest = hash_otp(code, salt=salt)
    return hmac.compare_digest(digest, stored_hash)


def otp_expiry(*, minutes: int = 15) -> str:
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
