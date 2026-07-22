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
    assert "Like talking to Siri" in page.text or "think," in page.text
    assert COOKIE_NAME in page.cookies
    assert page.cookies[COOKIE_NAME] == "en"


def test_language_switch_persists(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="lang-switch")
    client = TestClient(app)
    switched = client.post(
        "/lingua",
        data={"lang": "de", "next": "/login"},
        follow_redirects=False,
    )
    assert switched.status_code in {302, 303}
    assert switched.cookies.get(COOKIE_NAME) == "de"
    login = client.get("/login")
    assert "Anmelden" in login.text or "Einloggen" in login.text
    assert "Deutsch" in login.text
    assert "🇬🇧" in login.text or "🇮🇹" in login.text
