"""Validation helpers for account identity fields."""

from __future__ import annotations

import re

_EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
)
_NAME_RE = re.compile(r"^[^\d]+$", re.UNICODE)
_DIGITS_RE = re.compile(r"^\d+$")


def normalize_email(raw: str) -> str:
    email = (raw or "").strip().casefold()
    if not email:
        raise ValueError("L'email è obbligatoria.")
    if "@" not in email or "." not in email.split("@", 1)[-1]:
        raise ValueError(
            "Email non valida: serve @ e un'estensione (es. nome@gmail.com)."
        )
    if not _EMAIL_RE.match(email):
        raise ValueError(
            "Email non valida: serve @ e un'estensione (es. nome@gmail.com)."
        )
    if len(email) > 254:
        raise ValueError("Email troppo lunga.")
    return email


def validate_person_name(raw: str, *, field_label: str, required: bool = True) -> str:
    value = (raw or "").strip()
    if not value:
        if required:
            raise ValueError(f"{field_label} obbligatorio.")
        return ""
    if len(value) > 64:
        raise ValueError(f"{field_label} troppo lungo.")
    if any(ch.isdigit() for ch in value) or not _NAME_RE.match(value):
        raise ValueError(f"{field_label} non può contenere numeri.")
    return value


def digits_only(raw: str) -> str:
    return "".join(ch for ch in (raw or "") if ch.isdigit())


def is_digits(raw: str) -> bool:
    return bool(raw) and bool(_DIGITS_RE.match(raw))
