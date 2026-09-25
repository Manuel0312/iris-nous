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


def test_register_phone_optional_and_not_headset(tmp_path: Path) -> None:
    store = ProfileStore(tmp_path / "profiles")
    profile = store.create_account(
        "luca",
        "Segreta123",
        email="luca@gmail.com",
        headset_id="",
        phone_country="IT",
        phone_national="3339876543",
    )
    assert profile.phone_e164 == "+393339876543"
    assert profile.phone_country == "IT"
    assert profile.headset_id == ""
    assert profile.phone_label == ""

    bare = store.create_account("anna", "Segreta123", email="anna@gmail.com")
    assert bare.phone_e164 == ""
    done = store.update_anagrafica(
        "anna",
        first_name="Anna",
        last_name="",
        gender="female",
        email="anna@gmail.com",
        phone_country="",
        phone_national="",
    )
    assert done.anagrafica_complete is True
    assert done.phone_e164 == ""
    assert done.headset_id == ""


def test_data_backup_roundtrip(tmp_path: Path, monkeypatch) -> None:
    from bci_iot.accounts import data_backup as dbk

    secret = "test-backup-secret"
    monkeypatch.setenv("BCI_IOT_DATA_BACKUP", "1")
    monkeypatch.setenv("BCI_IOT_GITHUB_MAIL_TOKEN", "fake-token")
    monkeypatch.setenv("BCI_IOT_DATA_BACKUP_KEY", secret)

    root = tmp_path / "data"
    root.mkdir()
    (root / "accessi.db").write_bytes(b"sqlite-fake-content-for-backup-test")
    packed = dbk._pack_bundle(root)
    assert packed
    enc = dbk._encrypt(packed, secret)
    raw = dbk._decrypt(enc, secret)
    out = tmp_path / "restored"
    dbk._unpack_bundle(out, raw)
    assert (out / "accessi.db").read_bytes() == b"sqlite-fake-content-for-backup-test"
