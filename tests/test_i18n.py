"""Language detection and switching tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from bci_iot.web import create_app
from bci_iot.web.i18n import COOKIE_NAME, parse_accept_language, translate


def test_accept_language_and_translate() -> None:
    assert parse_accept_language("en-US,en;q=0.9,it;q=0.8") == "en"
    assert parse_accept_language("ja,en;q=0.5") == "ja"
    assert translate("en", "Login") == "Log in"
    assert translate("it", "Login") == "Login"
    assert translate("fr", "Iscriviti") == "S'inscrire"


def test_home_uses_detected_language(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="lang-secret")
    client = TestClient(app)
    page = client.get("/", headers={"Accept-Language": "en-GB,en;q=0.9"})
    assert page.status_code == 200
    assert "Il pensiero diventa azione" in page.text


def test_english_switch_persists(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="lang-en")
    client = TestClient(app)
    # Start from Italian browser, then switch to English via GET.
    client.get("/", headers={"Accept-Language": "it-IT,it;q=0.9"})
    switched = client.get("/lingua/en", follow_redirects=False)
    assert switched.status_code in {302, 303}
    assert switched.cookies.get(COOKIE_NAME) == "en"
    home = client.get("/")
    assert "Il pensiero diventa azione" in home.text
    login = client.get("/login")
    assert "Log in" in login.text or "Sign in" in login.text


def test_language_switch_persists(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="lang-switch")
    client = TestClient(app)
    switched = client.get("/lingua/de", follow_redirects=False)
    assert switched.status_code in {302, 303}
    assert switched.cookies.get(COOKIE_NAME) == "de"
    login = client.get("/login")
    assert "Anmelden" in login.text or "Einloggen" in login.text
    assert "Deutsch" in login.text
    assert "/flags/de.svg" in login.text
    assert "flagcdn.com" not in login.text


def test_local_flags_are_served(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="flag-assets")
    client = TestClient(app)
    home = client.get("/")
    assert home.status_code == 200
    assert "/flags/it.svg" in home.text
    assert "flagcdn.com" not in home.text
    flag = client.get("/flags/it.svg")
    assert flag.status_code == 200
    assert b"<svg" in flag.content
    gb = client.get("/flags/gb.svg")
    assert gb.status_code == 200
    un = client.get("/flags/un.svg")
    assert un.status_code == 200
    static_it = client.get("/static/flags/it.svg")
    assert static_it.status_code == 200
    assert b"<svg" in static_it.content


def test_local_site_banner_and_unknown_login(tmp_path: Path) -> None:
    app = create_app(
        data_dir=tmp_path,
        session_secret="local-hint",
        admin_username="admin",
        admin_password="admin123",
    )
    client = TestClient(app, base_url="http://127.0.0.1")
    home = client.get("/")
    assert "sito locale" in home.text.lower() or "sito online" in home.text.lower()
    assert "iris-nous.onrender.com" in home.text

    fail = client.post(
        "/login",
        data={"username": "inesistente", "password": "Segreta123"},
        follow_redirects=False,
    )
    assert fail.status_code == 200
    login_page = client.get("/login")
    assert "sito locale" in login_page.text.lower() or "telefono" in login_page.text.lower()

    admin_ok = client.post(
        "/login",
        data={"username": "Admin", "password": "admin123"},
        follow_redirects=False,
    )
    assert admin_ok.status_code == 200
    assert "/accessi" in admin_ok.text


def test_home_storytelling(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="home-story")
    client = TestClient(app)
    home = client.get("/")
    assert home.status_code == 200
    assert "headset.jpg" in home.text
    assert "Il pensiero diventa azione" in home.text
    assert "Il pensiero, in chiaro." in home.text
    assert "La casa ti ascolta." in home.text
    assert "Il ritmo, nel pensiero." in home.text
    assert "chat-fab" in home.text
    assert "Contattaci" in home.text
    assert "Manuel Bellomo" in home.text
    assert "lang-btn" in home.text
    assert "/flags/it.svg" in home.text
