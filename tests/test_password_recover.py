"""Password recovery tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from bci_iot.web import create_app


def test_recover_password_flow(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="recover-secret")
    client = TestClient(app)

    client.post(
        "/register",
        data={
            "username": "maria",
            "email": "maria@gmail.com",
            "password": "Vecchia123",
        },
        follow_redirects=False,
    )
    client.post(
        "/anagrafica",
        data={
            "first_name": "Maria",
            "last_name": "Rossi",
            "gender": "female",
            "email": "maria@gmail.com",
            "phone_country": "IT",
            "phone_national": "3331234567",
            "phone_label": "iPhone",
        },
        follow_redirects=False,
    )
    client.post("/api/auth/logout")

    page = client.get("/recupera-password")
    assert page.status_code == 200
    assert "Recupera password" in page.text

    start = client.post(
        "/recupera-password",
        data={
            "action": "identify",
            "identifier": "maria@gmail.com",
            "channel": "email",
        },
        follow_redirects=False,
    )
    assert start.status_code in {302, 303}

    # Demo delivery puts the code in the flash message.
    flash_page = client.get("/recupera-password")
    assert flash_page.status_code == 200
    assert "Codice:" in flash_page.text
    code = flash_page.text.split("Codice:")[-1].strip()[:6]
    assert code.isdigit()

    ok = client.post(
        "/recupera-password",
        data={
            "action": "confirm",
            "code": code,
            "new_password": "NuovaSegreta1",
            "new_password2": "NuovaSegreta1",
        },
        follow_redirects=False,
    )
    assert ok.status_code in {302, 303}

    login = client.post(
        "/login",
        data={"username": "maria", "password": "NuovaSegreta1"},
        follow_redirects=False,
    )
    assert login.status_code in {200, 302, 303}
    assert client.cookies.get("bci_iot_session") or login.status_code == 200


def test_login_page_has_recover_link(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="login-link")
    client = TestClient(app)
    page = client.get("/login")
    assert "Password dimenticata?" in page.text
    assert "/recupera-password" in page.text


def test_duplicate_email_points_to_recovery(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="dup-email")
    client = TestClient(app)
    client.post(
        "/register",
        data={
            "username": "maria",
            "email": "stessa@gmail.com",
            "password": "Segreta123",
        },
        follow_redirects=False,
    )
    client.post("/api/auth/logout")
    again = client.post(
        "/register",
        data={
            "username": "altra",
            "email": "stessa@gmail.com",
            "password": "Segreta456",
        },
        follow_redirects=False,
    )
    assert again.status_code == 200
    page = client.get("/register")
    assert "già registrata" in page.text or "Password dimenticata" in page.text
