"""Tests for multi-device login UI and authenticated config API."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from bci_iot.web import create_app


def _complete_anagrafica(client: TestClient, *, gender: str = "female") -> None:
    response = client.post(
        "/anagrafica",
        data={
            "first_name": "Maria",
            "last_name": "Rossi",
            "gender": gender,
            "phone_label": "iPhone di Maria",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "/calibrazione" in response.text


def _finish_calibration(client: TestClient) -> None:
    from bci_iot.pipeline.calibration_wizard import CALIBRATION_WORDS

    for word in CALIBRATION_WORDS:
        for _ in range(3):
            assert client.post("/api/calibrate/capture", json={"command": word}).status_code == 200
    assert client.post("/api/calibrate/finish").status_code == 200


def test_register_login_dashboard_flow(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="test-secret")
    client = TestClient(app)

    assert client.get("/health").json()["status"] == "ok"

    register = client.post(
        "/register",
        data={"username": "maria", "password": "Segreta123", "headset_id": ""},
        follow_redirects=False,
    )
    assert register.status_code == 200
    assert "/anagrafica" in register.text

    blocked = client.get("/dashboard", follow_redirects=False)
    assert blocked.status_code == 303
    assert blocked.headers["location"] == "/anagrafica"

    _complete_anagrafica(client, gender="female")

    # After anagrafica → calibration required
    blocked_cal = client.get("/dashboard", follow_redirects=False)
    assert blocked_cal.status_code == 303
    assert blocked_cal.headers["location"] == "/calibrazione"

    from bci_iot.pipeline.calibration_wizard import CALIBRATION_WORDS

    for word in CALIBRATION_WORDS:
        for _ in range(3):
            assert client.post("/api/calibrate/capture", json={"command": word}).status_code == 200
    assert client.post("/api/calibrate/finish").status_code == 200

    dash = client.get("/dashboard")
    assert dash.status_code == 200
    assert "Ciao, Maria" in dash.text
    assert "Cuffia" in dash.text or "Associata" in dash.text or "associa" in dash.text.lower()

    save = client.post(
        "/dashboard",
        data={
            "headset_id": "cuffia-001",
            "notes": "profilo personale",
            "action_focus": "spotify.next_track",
            "action_relax": "spotify.pause",
            "action_accept": "phone.accept_call",
            "action_reject": "phone.reject_call",
        },
        follow_redirects=False,
    )
    assert save.status_code == 303

    me = client.get("/api/me")
    assert me.status_code == 200
    body = me.json()
    assert body["username"] == "maria"
    assert body["first_name"] == "Maria"
    assert body["gender"] == "female"
    assert body["headset_id"] == "cuffia-001"
    assert "password_hash" not in body

    client.post("/logout", follow_redirects=False)
    assert client.get("/api/me").status_code == 401

    login = client.post(
        "/login",
        data={"username": "maria", "password": "Segreta123"},
        follow_redirects=False,
    )
    assert login.status_code == 200
    assert "/dashboard" in login.text
    assert client.get("/api/me").status_code == 200


def test_gendered_welcome_male_and_non_binary(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="gender-secret")
    client = TestClient(app)

    client.post(
        "/register",
        data={"username": "luca", "password": "Abcdef12", "headset_id": ""},
        follow_redirects=False,
    )
    _complete_anagrafica(client, gender="male")
    client.post(
        "/anagrafica",
        data={
            "first_name": "Luca",
            "last_name": "Bianchi",
            "gender": "male",
            "phone_label": "Pixel",
        },
        follow_redirects=False,
    )
    _finish_calibration(client)
    client.post("/logout", follow_redirects=False)
    login = client.post(
        "/login",
        data={"username": "luca", "password": "Abcdef12"},
        follow_redirects=False,
    )
    assert login.status_code == 200
    assert "/dashboard" in login.text
    dash = client.get("/dashboard")
    assert "Ciao, Luca" in dash.text

    client.post("/logout", follow_redirects=False)
    client.post(
        "/register",
        data={"username": "alex", "password": "Abcdef12", "headset_id": ""},
        follow_redirects=False,
    )
    client.post(
        "/anagrafica",
        data={
            "first_name": "Alex",
            "last_name": "",
            "gender": "non_binary",
            "phone_label": "Telefono Alex",
        },
        follow_redirects=False,
    )
    _finish_calibration(client)
    client.post("/logout", follow_redirects=False)
    login_nb = client.post(
        "/login",
        data={"username": "alex", "password": "Abcdef12"},
        follow_redirects=False,
    )
    assert "/dashboard" in login_nb.text
    dash_nb = client.get("/dashboard")
    assert "Ciao, Alex" in dash_nb.text


def test_api_auth_register_and_login(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="test-secret-api")
    client = TestClient(app)

    created = client.post(
        "/api/auth/register",
        json={"username": "luca", "password": "Abcdef12", "headset_id": "h-1"},
    )
    assert created.status_code == 200
    assert created.json()["headset_id"] == "h-1"
    assert created.json()["anagrafica_complete"] is False

    bad = client.post("/api/auth/login", json={"username": "luca", "password": "nope"})
    assert bad.status_code == 401

    ok = client.post("/api/auth/login", json={"username": "luca", "password": "Abcdef12"})
    assert ok.status_code == 200
    assert client.get("/api/me").json()["username"] == "luca"


def test_dashboard_requires_login(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="test-secret-guard")
    client = TestClient(app)
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
