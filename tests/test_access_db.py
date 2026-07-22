"""Tests for product site, auth, and SQLite access logs."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from bci_iot.accounts.access_db import AccessDatabase
from bci_iot.web import create_app


def test_access_database_roundtrip(tmp_path: Path) -> None:
    db = AccessDatabase(tmp_path / "t.db")
    db.log(username="maria", event="login_ok", ip="127.0.0.1", user_agent="pytest")
    db.log(username="maria", event="logout", ip="127.0.0.1")
    events = db.list_recent()
    assert len(events) == 2
    assert events[0].event == "logout"
    assert db.stats()["total"] == 2
    assert db.stats()["by_event"]["login_ok"] == 1


def test_product_home_and_dropdown(tmp_path: Path) -> None:
    app = create_app(
        data_dir=tmp_path,
        session_secret="home-secret",
        admin_username="admin",
        admin_password="admin123",
    )
    client = TestClient(app)
    page = client.get("/")
    assert page.status_code == 200
    assert "Iris" in page.text
    assert "Iris Nous" in page.text
    assert "pensando" in page.text or "Siri" in page.text
    assert "Login" in page.text
    assert "Iscrizione" in page.text
    assert "/static/brand/unito-di.png" in page.text
    assert "password-toggle" in client.get("/login").text
    assert "data-reveal" in page.text
    assert 'name="viewport"' in page.text
    assert 'data-theme-set="auto"' in page.text


def test_register_login_logged_and_admin_sees_accessi(tmp_path: Path) -> None:
    app = create_app(
        data_dir=tmp_path,
        session_secret="access-secret",
        admin_username="admin",
        admin_password="admin123",
    )
    client = TestClient(app)

    register = client.post(
        "/register",
        data={"username": "maria", "password": "Segreta123", "headset_id": ""},
        follow_redirects=False,
    )
    assert register.status_code == 200
    assert "/anagrafica" in register.text

    client.post(
        "/anagrafica",
        data={
            "first_name": "Maria",
            "last_name": "Rossi",
            "gender": "female",
            "phone_label": "iPhone",
        },
        follow_redirects=False,
    )

    client.post("/logout", follow_redirects=False)

    fail = client.post(
        "/login",
        data={"username": "maria", "password": "wrongpass"},
        follow_redirects=False,
    )
    assert fail.status_code == 200

    login = client.post(
        "/login",
        data={"username": "maria", "password": "Segreta123"},
        follow_redirects=False,
    )
    assert login.status_code == 200
    assert "/calibrazione" in login.text

    denied = client.get("/accessi", follow_redirects=False)
    assert denied.status_code == 303

    client.post("/logout", follow_redirects=False)
    admin_login = client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=False,
    )
    assert admin_login.status_code == 200
    assert "/accessi" in admin_login.text or "Accesso riuscito" in admin_login.text

    accessi = client.get("/accessi")
    assert accessi.status_code == 200
    assert "Pannello amministratore" in accessi.text
    assert "Maria" in accessi.text or "Rossi" in accessi.text

    detail = client.get("/accessi/utente/maria")
    assert detail.status_code == 200
    assert "login_ok" in detail.text or "register" in detail.text

    api = client.get("/api/admin/accessi")
    assert api.status_code == 200
    body = api.json()
    assert "people" in body
    assert body["stats"]["total"] >= 3
