"""Tests for local profile registration and authentication."""

from __future__ import annotations

from pathlib import Path

import pytest

from bci_iot.accounts import ProfileStore, verify_password
from bci_iot.accounts.validators import normalize_email, validate_person_name


def test_create_account_and_authenticate(tmp_path: Path) -> None:
    store = ProfileStore(tmp_path)
    created = store.create_account(
        "maria",
        "Segreta123",
        email="maria@gmail.com",
        headset_id="cuffia-demo-001",
    )
    assert created.username == "maria"
    assert created.email == "maria@gmail.com"
    assert created.headset_id == "cuffia-demo-001"
    assert verify_password("Segreta123", created.password_hash)

    loaded = store.get("maria")
    assert loaded is not None
    assert loaded.user_id == created.user_id

    assert store.authenticate("maria", "Segreta123") is not None
    assert store.authenticate("maria@gmail.com", "Segreta123") is not None
    assert store.authenticate("maria", "wrong") is None
    assert store.list_usernames() == ["maria"]


def test_duplicate_username_rejected(tmp_path: Path) -> None:
    store = ProfileStore(tmp_path)
    store.create_account("maria", "Segreta123", email="maria@gmail.com")
    with pytest.raises(ValueError, match="univoco|already|già"):
        store.create_account("maria", "Segreta456", email="altra@gmail.com")


def test_duplicate_email_rejected(tmp_path: Path) -> None:
    store = ProfileStore(tmp_path)
    store.create_account("maria", "Segreta123", email="stessa@gmail.com")
    with pytest.raises(ValueError, match="email|Password dimenticata"):
        store.create_account("luca", "Segreta456", email="stessa@gmail.com")


def test_name_rejects_digits_and_email_needs_domain(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        validate_person_name("Mar1a", field_label="Il nome")
    with pytest.raises(ValueError):
        normalize_email("senza-chiocciola")
    with pytest.raises(ValueError):
        normalize_email("a@b")
    assert normalize_email("Nome@Gmail.com") == "nome@gmail.com"

    store = ProfileStore(tmp_path)
    store.create_account("maria", "Segreta123", email="maria@gmail.com")
    with pytest.raises(ValueError, match="numeri"):
        store.update_anagrafica(
            "maria",
            first_name="Mar1a",
            last_name="Rossi",
            gender="female",
            email="maria@gmail.com",
            phone_country="IT",
            phone_national="3331234567",
        )


def test_update_config(tmp_path: Path) -> None:
    store = ProfileStore(tmp_path)
    store.create_account("maria", "Segreta123", email="maria@gmail.com")
    updated = store.update_config(
        "maria",
        headset_id="cuffia-002",
        notes="setup casa",
        action_map={"FOCUS": "spotify.next_track"},
    )
    assert updated.headset_id == "cuffia-002"
    assert updated.action_map["FOCUS"] == "spotify.next_track"


def test_otp_verify_email(tmp_path: Path) -> None:
    store = ProfileStore(tmp_path)
    store.create_account("maria", "Segreta123", email="maria@gmail.com")
    store.update_anagrafica(
        "maria",
        first_name="Maria",
        last_name="Rossi",
        gender="female",
        email="maria@gmail.com",
        phone_country="IT",
        phone_national="3331234567",
    )
    profile, code = store.issue_otp("maria", channel="email", purpose="verify_email")
    assert profile.email_verified is False
    verified = store.consume_otp("maria", code=code, purpose="verify_email")
    assert verified.email_verified is True
