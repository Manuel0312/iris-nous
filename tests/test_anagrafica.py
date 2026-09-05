"""Tests for Italian gender-aware greetings and anagrafica."""

from __future__ import annotations

from pathlib import Path

import pytest

from bci_iot.accounts.access_db import AccessDatabase
from bci_iot.accounts.gender import normalize_gender, welcome_back, welcome_new
from bci_iot.accounts.store import ProfileStore


def test_normalize_gender_and_greetings() -> None:
    assert normalize_gender("donna") == "female"
    assert normalize_gender("uomo") == "male"
    assert normalize_gender("non binario") == "non_binary"
    with pytest.raises(ValueError):
        normalize_gender("altro")

    assert "Bentornata, Maria" in welcome_back(
        first_name="Maria", username="m", gender="female"
    )
    assert "Bentornato, Luca" in welcome_back(
        first_name="Luca", username="l", gender="male"
    )
    assert "Bentornatə, Alex" in welcome_back(
        first_name="Alex", username="a", gender="non_binary"
    )
    assert "Benvenuta" in welcome_new(
        first_name="Maria", username="m", gender="female"
    )


def test_anagrafica_persisted_and_mirrored_to_sqlite(tmp_path: Path) -> None:
    store = ProfileStore(tmp_path / "profiles")
    db = AccessDatabase(tmp_path / "accessi.db")
    store.create_account("maria", "Segreta123", email="maria@gmail.com")
    profile = store.update_anagrafica(
        "maria",
        first_name="Maria",
        last_name="Rossi",
        gender="female",
        email="maria@gmail.com",
        phone_country="IT",
        phone_national="3331234567",
        phone_label="iPhone",
    )
    assert profile.anagrafica_complete is True
    assert profile.gender == "female"
    assert profile.phone_e164 == "+393331234567"
    db.upsert_anagrafica(
        username=profile.username,
        user_id=profile.user_id,
        first_name=profile.first_name,
        last_name=profile.last_name,
        gender=profile.gender,
        phone_label=profile.phone_label,
        headset_id=profile.headset_id,
        email=profile.email,
        phone_e164=profile.phone_e164,
    )
    with db._connect() as conn:
        row = conn.execute(
            "SELECT first_name, gender, email, phone_e164 FROM user_anagrafica WHERE username=?",
            ("maria",),
        ).fetchone()
    assert row["first_name"] == "Maria"
    assert row["gender"] == "female"
    assert row["email"] == "maria@gmail.com"
    assert row["phone_e164"] == "+393331234567"
