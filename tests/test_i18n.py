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
    assert "Thought becomes action" in page.text
    assert "Il pensiero diventa azione" not in page.text


def test_english_switch_persists(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="lang-en")
    client = TestClient(app)
    # Start from Italian browser, then switch to English via GET.
    client.get("/", headers={"Accept-Language": "it-IT,it;q=0.9"})
    switched = client.get("/lingua/en", follow_redirects=False)
    assert switched.status_code in {302, 303}
    assert switched.cookies.get(COOKIE_NAME) == "en"
    home = client.get("/")
    assert "Thought becomes action" in home.text
    assert "think," in home.text
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


def test_spanish_is_supported(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="lang-es")
    client = TestClient(app)
    switched = client.get("/lingua/es", follow_redirects=False)
    assert switched.status_code in {302, 303}
    assert switched.cookies.get(COOKIE_NAME) == "es"
    login = client.get("/login")
    assert "Español" in login.text
    assert "/flags/es.svg" in login.text
    assert "Iniciar sesión" in login.text
    es_flag = client.get("/flags/es.svg")
    assert es_flag.status_code == 200
    assert b"<svg" in es_flag.content
    home_es = client.get("/")
    assert "piensa," in home_es.text or "Piensa" in home_es.text or "piensa" in home_es.text.lower()
    assert "El pensamiento se convierte en acción" in home_es.text
    assert 'href="/lingua/es"' in home_es.text
    assert 'href="/lingua/ja"' in home_es.text
    assert 'href="/lingua/zh"' in home_es.text


def test_japanese_and_chinese_switch(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="lang-cjk")
    client = TestClient(app)
    ja = client.get("/lingua/ja", follow_redirects=False)
    assert ja.status_code in {302, 303}
    assert ja.cookies.get(COOKIE_NAME) == "ja"
    login_ja = client.get("/login")
    assert "ログイン" in login_ja.text
    assert "Noto+Sans+JP" in login_ja.text
    zh = client.get("/lingua/zh", follow_redirects=False)
    assert zh.cookies.get(COOKIE_NAME) == "zh"
    login_zh = client.get("/login")
    assert "登录" in login_zh.text
    home_ja = client.get("/lingua/ja", follow_redirects=True)
    assert "考え、" in home_ja.text
    assert "思考が行動になる" in home_ja.text
    home_zh = client.get("/lingua/zh", follow_redirects=True)
    assert "思考，" in home_zh.text or "思考化为行动" in home_zh.text
    posted = client.post("/lingua", data={"lang": "es", "next": "/login"}, follow_redirects=False)
    assert posted.status_code in {302, 303}
    assert posted.cookies.get(COOKIE_NAME) == "es"


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


def test_login_does_not_expose_admin_credentials(tmp_path: Path) -> None:
    app = create_app(
        data_dir=tmp_path,
        session_secret="no-creds-on-login",
        admin_username="admin",
        admin_password="admin123",
    )
    client = TestClient(app, base_url="https://iris-nous.onrender.com")
    page = client.get("/login")
    assert page.status_code == 200
    assert "admin123" not in page.text
    assert "Accesso amministratore" not in page.text
    assert "Thesis admin login" not in page.text
    assert "default password" not in page.text.lower()


def test_stale_env_secret_still_allows_thesis_admin(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("BCI_IOT_ADMIN_PASSWORD", "GeneratedOld99")
    app = create_app(data_dir=tmp_path, session_secret="stale-env")
    client = TestClient(app)
    ok = client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=False,
    )
    assert ok.status_code == 200
    assert "/accessi" in ok.text


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
    assert "errore=1" in fail.text
    login_page = client.get("/login")
    assert "sito locale" in login_page.text.lower() or "telefono" in login_page.text.lower()

    admin_ok = client.post(
        "/login",
        data={"username": "Admin", "password": "admin123"},
        follow_redirects=False,
    )
    assert admin_ok.status_code == 200
    assert "/accessi" in admin_ok.text


def test_signup_shows_code_when_mail_cannot_send(tmp_path: Path, monkeypatch) -> None:
    import importlib

    from bci_iot.accounts.messaging import DeliveryResult

    monkeypatch.setenv("BCI_IOT_OTP_DEMO", "0")
    monkeypatch.delenv("BCI_IOT_HTTPS", raising=False)
    monkeypatch.delenv("BCI_IOT_SMTP_HOST", raising=False)
    monkeypatch.delenv("BCI_IOT_RESEND_API_KEY", raising=False)

    def fake_send(**kwargs):
        return DeliveryResult(
            ok=False,
            channel="email",
            destination=str(kwargs.get("destination") or ""),
            mode="demo",
            detail="smtp missing",
            demo_code=str(kwargs.get("code") or ""),
        )

    webapp = importlib.import_module("bci_iot.web.app")
    monkeypatch.setattr(webapp, "send_signup_confirmation", fake_send, raising=False)
    app = create_app(data_dir=tmp_path, session_secret="signup-mail")
    client = TestClient(app)
    created = client.post(
        "/register",
        data={
            "username": "luca",
            "email": "luca@gmail.com",
            "password": "Segreta123",
        },
        follow_redirects=False,
    )
    assert created.status_code == 200
    wait = client.get("/attendi-conferma-email", follow_redirects=False)
    assert wait.status_code == 200
    assert "Conferma la tua email" in wait.text
    assert "otp-preview" in wait.text
    chat = client.get("/chatta")
    assert "Agente AI" not in chat.text
    assert "bg3d.js" in chat.text


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
    assert "Chatta con noi" in home.text
    assert "canale=email" not in home.text
    assert "Manuel Bellomo" in home.text
    assert "lang-btn" in home.text
    assert "/flags/it.svg" in home.text
    assert 'class="theme-switch"' not in home.text
    assert "data-theme-set" not in home.text
    assert "unito-home" in home.text
    assert 'href="/login"' in home.text
    assert 'href="/register"' in home.text
    css = client.get("/static/styles.css")
    assert css.status_code == 200
    assert "public, max-age=86400" in css.headers.get("cache-control", "")
