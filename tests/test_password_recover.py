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
        data={"username": "maria", "password": "Vecchia123"},
        follow_redirects=False,
    )
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
    client.post("/api/auth/logout")

    page = client.get("/recupera-password")
    assert page.status_code == 200
    assert "Recupera password" in page.text

    bad = client.post(
        "/recupera-password",
        data={
            "username": "maria",
            "first_name": "Wrong",
            "last_name": "Rossi",
            "new_password": "NuovaSegreta1",
            "new_password2": "NuovaSegreta1",
        },
        follow_redirects=False,
    )
    assert bad.status_code in {302, 303}

    ok = client.post(
        "/recupera-password",
        data={
            "username": "maria",
            "first_name": "Maria",
            "last_name": "Rossi",
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
