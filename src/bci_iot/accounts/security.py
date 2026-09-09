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
class PasswordRequirement:
    id: str
    label: str
    ok: bool
    optional: bool = False


@dataclass(frozen=True, slots=True)
class PasswordCheck:
    ok: bool
    level: StrengthLevel
    message: str
    requirements: tuple[PasswordRequirement, ...] = ()


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


def secrets_equal(left: str, right: str) -> bool:
    """Compare two secrets without leaking length via compare_digest errors."""

    if not left or not right:
        return False
    a = left.encode("utf-8")
    b = right.encode("utf-8")
    if len(a) != len(b):
        return False
    return hmac.compare_digest(a, b)


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


def password_requirements(password: str) -> tuple[PasswordRequirement, ...]:
    """Interactive checklist: mandatory red→green; optional/recommended yellow→green."""

    pwd = password or ""
    return (
        PasswordRequirement("len", "Almeno 8 caratteri", len(pwd) >= 8),
        PasswordRequirement("upper", "Almeno una lettera maiuscola", bool(re.search(r"[A-Z]", pwd))),
        PasswordRequirement("digit", "Almeno un numero", bool(re.search(r"[0-9]", pwd))),
        PasswordRequirement(
            "lower",
            "Almeno una lettera minuscola (consigliato)",
            bool(re.search(r"[a-z]", pwd)),
            optional=True,
        ),
        PasswordRequirement(
            "special",
            "Almeno un carattere speciale (consigliato)",
            bool(re.search(r"[^A-Za-z0-9]", pwd)),
            optional=True,
        ),
        PasswordRequirement(
            "long",
            "Almeno 12 caratteri (consigliato)",
            len(pwd) >= 12,
            optional=True,
        ),
    )


def password_strength(password: str) -> PasswordCheck:
    """Evaluate password; registration requires at least medium."""

    reqs = password_requirements(password)
    if not password:
        return PasswordCheck(
            False,
            "weak",
            "Password non abbastanza forte",
            requirements=reqs,
        )

    has_upper = bool(re.search(r"[A-Z]", password))
    has_digit = bool(re.search(r"[0-9]", password))
    has_lower = bool(re.search(r"[a-z]", password))
    has_special = bool(re.search(r"[^A-Za-z0-9]", password))
    length = len(password)
    # Mandatory for "ok": length, upper, digit.
    mandatory_ok = all(r.ok for r in reqs if r.id in {"len", "upper", "digit"})

    if not mandatory_ok:
        return PasswordCheck(
            False,
            "weak",
            "Password non abbastanza forte: almeno 8 caratteri, una maiuscola e un numero.",
            requirements=reqs,
        )

    if length >= 12 and has_lower and has_special:
        return PasswordCheck(True, "strong", "Password forte", requirements=reqs)
    return PasswordCheck(True, "medium", "Password di livello medio", requirements=reqs)
