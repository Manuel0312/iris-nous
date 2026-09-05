"""Tests for password hashing helpers."""

from __future__ import annotations

from bci_iot.accounts.security import hash_password, password_strength, verify_password


def test_hash_and_verify_roundtrip() -> None:
    hashed = hash_password("prova-password")
    assert hashed.startswith("scrypt$")
    assert verify_password("prova-password", hashed) is True
    assert verify_password("altra", hashed) is False


def test_password_strength_requires_medium() -> None:
    weak = password_strength("segreta123")
    assert weak.ok is False
    assert weak.level == "weak"
    medium = password_strength("Segreta123")
    assert medium.ok is True
    assert medium.level in {"medium", "strong"}
