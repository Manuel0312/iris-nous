"""Tests for local profile registration and authentication."""

from __future__ import annotations

from pathlib import Path

import pytest

from bci_iot.accounts import ProfileStore, verify_password


def test_create_account_and_authenticate(tmp_path: Path) -> None:
    store = ProfileStore(tmp_path)
    created = store.create_account("maria", "Segreta123", headset_id="cuffia-demo-001")
    assert created.username == "maria"
    assert created.headset_id == "cuffia-demo-001"
    assert verify_password("Segreta123", created.password_hash)

    loaded = store.get("maria")
    assert loaded is not None
    assert loaded.user_id == created.user_id

    assert store.authenticate("maria", "Segreta123") is not None
    assert store.authenticate("maria", "wrong") is None
    assert store.list_usernames() == ["maria"]


def test_duplicate_username_rejected(tmp_path: Path) -> None:
    store = ProfileStore(tmp_path)
    store.create_account("maria", "Segreta123")
    with pytest.raises(ValueError, match="univoco|already|già"):
        store.create_account("maria", "Segreta456")


def test_update_config(tmp_path: Path) -> None:
    store = ProfileStore(tmp_path)
    store.create_account("maria", "Segreta123")
    updated = store.update_config(
        "maria",
        headset_id="cuffia-002",
        notes="setup casa",
        action_map={"FOCUS": "spotify.next_track"},
    )
    assert updated.headset_id == "cuffia-002"
    assert updated.action_map["FOCUS"] == "spotify.next_track"
