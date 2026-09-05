"""ProfileStore persists on SQLite (AccessDatabase.users), not JSON files."""

from __future__ import annotations

from pathlib import Path

from bci_iot.accounts.access_db import AccessDatabase
from bci_iot.accounts.store import ProfileStore


def test_profile_store_sqlite_roundtrip(tmp_path: Path) -> None:
    db = AccessDatabase(tmp_path / "accessi.db")
    store = ProfileStore(tmp_path, access_db=db)
    created = store.create_account(
        "luca", "Segreta123", email="luca@gmail.com", headset_id="h1"
    )
    assert created.username == "luca"
    assert not list(tmp_path.glob("*.json"))
    assert not list((tmp_path / "profiles").glob("*.json")) if (tmp_path / "profiles").exists() else True

    loaded = store.get("luca")
    assert loaded is not None
    assert loaded.user_id == created.user_id
    assert loaded.email == "luca@gmail.com"

    row = db.get_user("luca")
    assert row is not None
    assert row["password_hash"]
    assert row["email"] == "luca@gmail.com"


def test_migrate_legacy_json_into_sqlite(tmp_path: Path) -> None:
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    legacy = ProfileStore.__new__(ProfileStore)
    # Write a JSON the old way once, then open a fresh SQLite-backed store.
    from bci_iot.accounts.store import UserProfile
    from bci_iot.accounts.security import hash_password
    import json

    profile = UserProfile(
        username="anna",
        password_hash=hash_password("Segreta123"),
        email="anna@gmail.com",
        user_id="uid-anna",
    )
    (profiles / "anna.json").write_text(json.dumps(profile.to_dict()), encoding="utf-8")

    db = AccessDatabase(tmp_path / "accessi.db")
    store = ProfileStore(profiles, access_db=db)
    loaded = store.get("anna")
    assert loaded is not None
    assert loaded.email == "anna@gmail.com"
    assert (profiles / "anna.json.migrated").exists()
