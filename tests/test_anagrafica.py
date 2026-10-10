"""Tests for Italian gender-aware greetings and anagrafica."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bci_iot.accounts.access_db import AccessDatabase
from bci_iot.accounts.gender import normalize_gender, welcome_back, welcome_new
from bci_iot.accounts.store import ProfileStore
from bci_iot.web import create_app

def test_normalize_gender_and_greetings() -> None:
    assert normalize_gender("donna") == "female"
    assert normalize_gender("uomo") == "male"
    assert normalize_gender("non binario") == "non_binary"
    with pytest.raises(ValueError):
        normalize_gender("altro")

    assert welcome_back(first_name="Maria", username="m", gender="female") == (
        "Che bello rivederti, Maria."
    )
    assert welcome_back(first_name="Luca", username="l", gender="male") == (
        "Che bello rivederti, Luca."
    )
    assert welcome_back(first_name="Alex", username="a", gender="non_binary") == (
        "Che bello rivederti, Alex."
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


def test_backup_enabled_on_render_when_mail_token_present(monkeypatch) -> None:
    from bci_iot.accounts import data_backup as dbk

    monkeypatch.delenv("BCI_IOT_DATA_BACKUP", raising=False)
    monkeypatch.delenv("BCI_IOT_ENV", raising=False)
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("BCI_IOT_GITHUB_MAIL_TOKEN", "ghp_test_token")
    monkeypatch.setenv("BCI_IOT_SESSION_SECRET", "session-secret")
    assert dbk._enabled() is True
    monkeypatch.setenv("BCI_IOT_DATA_BACKUP", "0")
    assert dbk._enabled() is False


def test_backup_refuses_overwrite_richer_remote(tmp_path: Path, monkeypatch) -> None:
    """Admin-only local DB must not replace a remote bundle that has real users."""
    from bci_iot.accounts import data_backup as dbk
    from bci_iot.accounts.access_db import AccessDatabase
    from bci_iot.accounts.store import ProfileStore

    secret = "refuse-overwrite-secret"
    monkeypatch.setenv("BCI_IOT_DATA_BACKUP", "1")
    monkeypatch.setenv("BCI_IOT_GITHUB_MAIL_TOKEN", "fake-token")
    monkeypatch.setenv("BCI_IOT_DATA_BACKUP_KEY", secret)
    monkeypatch.setenv("BCI_IOT_DATA_BACKUP_BRANCH", "iris-data")

    rich = tmp_path / "rich"
    rich.mkdir()
    store_rich = ProfileStore(rich)
    store_rich.ensure_admin("admin", "admin123")
    store_rich.create_account(
        "maria",
        "Maria123!",
        email="maria@gmail.com",
    )
    packed = dbk._pack_bundle(rich)
    assert packed
    enc = dbk._encrypt(packed, secret)
    assert dbk._count_users_in_encrypted(enc) >= 2

    empty = tmp_path / "empty"
    empty.mkdir()
    store_empty = ProfileStore(empty)
    store_empty.ensure_admin("admin", "admin123")
    assert store_empty.db.count_users(exclude_admin=True) == 0

    remote = {
        "content": __import__("base64").b64encode(enc).decode("ascii"),
        "sha": "abc123",
    }
    calls: list[str] = []

    def fake_api(method, url_path, payload=None):
        calls.append(f"{method}:{url_path}")
        if method.upper() == "GET" and "contents/" in url_path:
            return remote
        if method.upper() == "PUT":
            raise AssertionError("must not upload over richer remote")
        if method.upper() == "GET" and "/git/ref/" in url_path:
            return {"object": {"sha": "deadbeef"}}
        return None

    monkeypatch.setattr(dbk, "_api", fake_api)
    dbk.record_boot_restore(False, "simulate failed restore")
    assert dbk.backup_data_dir(empty, force=True) is False
    assert "refuse" in str(dbk.backup_status(data_root=empty).get("last_error") or "").lower() or dbk.backup_status(
        data_root=empty
    ).get("upload_blocked")


def test_anagrafica_photo_crop_ui(tmp_path: Path) -> None:
    app = create_app(
        data_dir=tmp_path,
        session_secret="photo-crop",
        admin_username="admin",
        admin_password="admin123",
    )
    client = TestClient(app)
    store = app.state.store
    store.create_account("ve", "Segreta123", email="ve@gmail.com")
    profile = store.get("ve")
    assert profile is not None
    profile.email_verified = True
    store.save(profile)
    client.post("/login", data={"username": "ve", "password": "Segreta123"})
    page = client.get("/anagrafica")
    assert page.status_code == 200
    assert "photo-crop-editor" in page.text
    assert "photo-crop-canvas" in page.text
    assert "photo-zoom" in page.text
    assert "photo_crop.js" in page.text
    assert "Ingrandimento" in page.text
    assert "photo-face-dialog" in page.text
    assert "anag-photo" in page.text
    assert "Va bene anche dopo" not in page.text
    assert "Come ti chiami" in page.text
    assert "Come ti senti" in page.text
    assert "anag-card" in page.text
    assert "I tuoi dati personali" in page.text
    assert "Email verificata" in page.text or "photo-face-dialog" in page.text
    assert "avatar hero" in page.text or 'class="avatar hero"' in page.text


def test_admin_database_people_page(tmp_path: Path) -> None:
    app = create_app(
        data_dir=tmp_path,
        session_secret="db-people",
        admin_username="admin",
        admin_password="admin123",
    )
    client = TestClient(app)
    client.post("/login", data={"username": "admin", "password": "admin123"})
    store = app.state.store
    store.create_account(
        "luca",
        "Luca1234!",
        email="luca@gmail.com",
    )
    page = client.get("/accessi/database")
    assert page.status_code == 200
    assert "Database persone" in page.text
    assert "luca" in page.text
    assert "luca@gmail.com" in page.text
    assert 'action="/accessi/database/backup"' not in page.text
    assert "Backup attivo" not in page.text
    assert "Token GitHub" not in page.text
    assert "Tutti gli account registrati" in page.text
    accessi = client.get("/accessi")
    assert 'href="/accessi/database"' in accessi.text
    accounts = app.state.access_db.list_all_accounts()
    assert any(a["username"] == "luca" for a in accounts)
