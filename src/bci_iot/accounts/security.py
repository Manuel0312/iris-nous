"""Password hashing helpers for local account authentication."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass
from typing import Literal


StrengthLevel = Literal["weak", "medium", "strong"]


@dataclass(frozen=True, slots=True)
class PasswordCheck:
    ok: bool
    level: StrengthLevel
    message: str


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    """Return a portable ``scrypt`` password hash string.

    Format: ``scrypt$<salt_hex>$<hash_hex>``.
    """

    if not password:
        raise ValueError("password must be non-empty")
    salt_bytes = salt if salt is not None else secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt_bytes,
        n=2**14,
        r=8,
        p=1,
        dklen=32,
    )
    return f"scrypt${salt_bytes.hex()}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    """Constant-time verification of ``password`` against a stored hash."""

    try:
        algo, salt_hex, _digest_hex = password_hash.split("$", 2)
    except ValueError:
        return False
    if algo != "scrypt":
        return False
    candidate = hash_password(password, salt=bytes.fromhex(salt_hex))
    return hmac.compare_digest(candidate, password_hash)


def password_strength(password: str) -> PasswordCheck:
    """Evaluate password; registration requires at least medium."""

    if not password:
        return PasswordCheck(False, "weak", "Password non abbastanza forte")

    has_upper = bool(re.search(r"[A-Z]", password))
    has_digit = bool(re.search(r"[0-9]", password))
    has_lower = bool(re.search(r"[a-z]", password))
    has_special = bool(re.search(r"[^A-Za-z0-9]", password))
    length = len(password)

    if length < 8 or not has_upper or not has_digit:
        return PasswordCheck(
            False,
            "weak",
            "Password non abbastanza forte: almeno 8 caratteri, una maiuscola e un numero.",
        )

    if length >= 12 and has_lower and has_special:
        return PasswordCheck(True, "strong", "Password forte")
    return PasswordCheck(True, "medium", "Password di livello medio")
