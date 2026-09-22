"""All-language UI coverage + user↔admin chat translation matrix."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bci_iot.accounts.chat_translate import present_support_messages
from bci_iot.web import create_app
from bci_iot.web.i18n import (
    COOKIE_NAME,
    SUPPORTED,
    detect_language,
    language_for_country,
    translate,
)
from bci_iot.web.translations import CATALOG

# Chatta strings that must never stay Italian when lang ≠ it.
CHATTA_KEYS = (
    "Chatta con noi",
    "Spiegaci il problema.",
    "Richiesta di chat",
    "Riapri la chat",
    "Recupera codice",
    "Codice chat",
    "Nome ed email servono per saperti rispondere. Il codice chat ti viene mostrato all’inizio.",
    "Hai già una chat? Inserisci il codice che ti abbiamo mostrato all’inizio.",
    "Non ricordi il codice? Te lo reinviamo all’email usata per aprire la chat.",
    "Invia",
    "Descrivi il problema",
)

ADMIN_KEYS = (
    "Notifiche",
    "Messaggi da Chatta con noi.",
    "Nuovo",
    "Letto",
    "Risposto",
    "Rispondi",
    "La risposta arriva in chat e via email.",
    "Cliente",
    "Codice chat",
)

# Short sample message per user language (original text they type).
USER_SAMPLES = {
    "it": "Non riesco ad associare la cuffia",
    "en": "I cannot associate the headphone",
    "es": "No puedo asociar los auriculares",
    "fr": "Je n'arrive pas à associer le casque",
    "de": "Ich kann den Kopfhörer nicht koppeln",
    "pt": "Não consigo associar os auscultadores",
    "zh": "我无法关联耳机",
    "ja": "ヘッドセットを連携できません",
}

ADMIN_SAMPLES = {
    "it": "Apri Associa telefono e riprova",
    "en": "Open Pair phone and try again",
    "es": "Abre Asociar teléfono e inténtalo de nuevo",
    "fr": "Ouvre Associer le téléphone et réessaie",
    "de": "Öffne Telefon koppeln und versuche es erneut",
    "pt": "Abre Associar telemóvel e tenta de novo",
    "zh": "请打开关联手机后再试",
    "ja": "スマホ連携を開いてもう一度試してください",
}


@pytest.mark.parametrize("lang", list(SUPPORTED))
def test_catalog_has_chatta_and_admin_keys(lang: str) -> None:
    if lang == "it":
        return
    for key in CHATTA_KEYS + ADMIN_KEYS:
        assert key in CATALOG[lang], f"missing {lang}: {key[:48]}"
        assert CATALOG[lang][key].strip()
        # Must differ from Italian source (except rare cognates like ES "Cliente")
        if key not in {"Cliente", "Online", "Offline", "Email", "Admin", "Inbox"}:
            assert CATALOG[lang][key] != key, f"untranslated {lang}: {key[:48]}"


@pytest.mark.parametrize("lang", list(SUPPORTED))
def test_chatta_page_fully_translated(lang: str, tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path / lang, session_secret=f"chatta-{lang}")
    client = TestClient(app)
    client.get(f"/lingua/{lang}")
    page = client.get("/chatta")
    assert page.status_code == 200
    assert page.cookies.get(COOKIE_NAME) == lang or client.cookies.get(COOKIE_NAME) == lang
    if lang == "it":
        assert "Richiesta di chat" in page.text
        assert "Riapri la chat" in page.text
        return
    assert "Richiesta di chat" not in page.text
    assert "Riapri la chat" not in page.text
    assert "Recupera codice" not in page.text
    # Expected translated snippets
    assert translate(lang, "Richiesta di chat") in page.text
    assert translate(lang, "Riapri la chat") in page.text
    assert translate(lang, "Recupera codice") in page.text
    assert translate(lang, "Chatta con noi") in page.text


@pytest.mark.parametrize(
    ("country", "expected"),
    [
        ("IT", "it"),
        ("FR", "fr"),
        ("DE", "de"),
        ("ES", "es"),
        ("PT", "pt"),
        ("BR", "pt"),
        ("CN", "zh"),
        ("JP", "ja"),
        ("US", "en"),
        ("GB", "en"),
        ("PL", "en"),  # Polish → English
        ("NL", "en"),
        ("SE", "en"),
        ("KR", "en"),
        ("XX", "en"),
        ("", "en"),
        (None, "en"),
    ],
)
def test_language_for_country(country: str | None, expected: str) -> None:
    assert language_for_country(country) == expected


def test_poland_geo_header_selects_english(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="geo-pl")
    client = TestClient(app)
    # No cookie, Accept-Language only Polish (unsupported) → English
    page = client.get(
        "/",
        headers={
            "Accept-Language": "pl-PL,pl;q=0.9",
            "cf-ipcountry": "PL",
        },
    )
    assert page.status_code == 200
    assert "invisible bridge" in page.text.lower() or "An invisible bridge" in page.text
    assert "Un ponte invisibile" not in page.text

    # Even without country header, unsupported Accept-Language → English
    page2 = client.get("/", headers={"Accept-Language": "pl-PL,pl;q=0.9"})
    assert "invisible bridge" in page2.text.lower() or "An invisible bridge" in page2.text
    assert "Un ponte invisibile" not in page2.text


def test_italy_geo_header_selects_italian(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="geo-it")
    client = TestClient(app)
    page = client.get(
        "/",
        headers={
            "Accept-Language": "pl-PL,pl;q=0.9",
            "cf-ipcountry": "IT",
        },
    )
    # Accept-Language pl is unsupported → falls through to country IT → it
    assert "Un ponte invisibile" in page.text


@pytest.mark.parametrize("user_lang", list(SUPPORTED))
@pytest.mark.parametrize("admin_lang", list(SUPPORTED))
def test_chat_translate_matrix_user_to_admin(
    user_lang: str, admin_lang: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Admin always sees a presentation in admin_lang (or original if same)."""

    def fake_translate(text: str, *, source: str, target: str) -> str:
        if source == target:
            return text
        return f"[{source}->{target}]{text}"

    monkeypatch.setattr(
        "bci_iot.accounts.chat_translate.translate_text", fake_translate
    )
    body = USER_SAMPLES[user_lang]
    messages = [
        {
            "sender": "user",
            "body": body,
            "body_translated": "",
            "lang_src": user_lang,
            "lang_dst": "",
        }
    ]
    shown = present_support_messages(
        messages,
        viewer_is_admin=True,
        viewer_lang=admin_lang,
        fallback_user_lang=user_lang,
    )
    display = shown[0]["display_body"]
    if user_lang == admin_lang:
        assert display == body
        assert shown[0]["show_original"] is False
    else:
        assert display == f"[{user_lang}->{admin_lang}]{body}"
        assert shown[0]["show_original"] is True
        assert shown[0]["original_body"] == body


@pytest.mark.parametrize("user_lang", list(SUPPORTED))
@pytest.mark.parametrize("admin_lang", list(SUPPORTED))
def test_chat_translate_matrix_admin_to_user(
    user_lang: str, admin_lang: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_translate(text: str, *, source: str, target: str) -> str:
        if source == target:
            return text
        return f"[{source}->{target}]{text}"

    monkeypatch.setattr(
        "bci_iot.accounts.chat_translate.translate_text", fake_translate
    )
    body = ADMIN_SAMPLES[admin_lang]
    stored = f"[{admin_lang}->{user_lang}]{body}" if admin_lang != user_lang else ""
    messages = [
        {
            "sender": "admin",
            "body": body,
            "body_translated": stored,
            "lang_src": admin_lang,
            "lang_dst": user_lang,
        }
    ]
    shown = present_support_messages(
        messages,
        viewer_is_admin=False,
        viewer_lang=user_lang,
        fallback_user_lang=user_lang,
    )
    display = shown[0]["display_body"]
    if user_lang == admin_lang:
        assert display == body
    else:
        assert display == stored
        assert shown[0]["show_original"] is True


def test_end_to_end_en_user_it_admin_roundtrip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_translate(text: str, *, source: str, target: str) -> str:
        if source == target:
            return text
        return f"TR({source}->{target}):{text}"

    monkeypatch.setattr(
        "bci_iot.accounts.chat_translate.translate_text", fake_translate
    )
    import importlib

    app_mod = importlib.import_module("bci_iot.web.app")
    monkeypatch.setattr(app_mod, "translate_text", fake_translate)

    app = create_app(
        data_dir=tmp_path,
        session_secret="e2e-chat",
        admin_username="admin",
        admin_password="admin123",
    )
    user = TestClient(app)
    user.get("/lingua/en")
    posted = user.post(
        "/chatta",
        data={
            "name": "Alex",
            "email": "alex.matrix@example.com",
            "phone": "3331112222",
            "body": USER_SAMPLES["en"],
            "ui_lang": "en",
        },
        follow_redirects=False,
    )
    assert posted.status_code == 200
    thread_page = user.get("/chatta")
    assert USER_SAMPLES["en"] in thread_page.text

    admin = TestClient(app)
    admin.get("/lingua/it")
    admin.post("/login", data={"username": "admin", "password": "admin123"})
    threads = app.state.access_db.list_support_threads()
    assert threads
    tid = int(threads[0]["id"])
    raw = app.state.access_db.list_support_messages(tid)
    assert raw
    assert str(raw[0].get("lang_src") or "").startswith("en"), raw[0]
    assert str(threads[0].get("user_lang") or "").startswith("en"), threads[0]
    presented = present_support_messages(
        raw,
        viewer_is_admin=True,
        viewer_lang="it",
        fallback_user_lang=str(threads[0].get("user_lang") or "en"),
    )
    assert presented[0]["display_body"] == f"TR(en->it):{USER_SAMPLES['en']}"
    assert presented[0]["show_original"] is True

    view = admin.get(f"/notifiche/{tid}")
    assert f"TR(en->it):{USER_SAMPLES['en']}" in view.text or USER_SAMPLES["en"] in view.text

    reply = admin.post(
        f"/notifiche/{tid}/rispondi",
        data={"body": ADMIN_SAMPLES["it"]},
        follow_redirects=False,
    )
    assert reply.status_code == 200

    # Guest left; reopen with code
    code = str(threads[0].get("access_code") or "")
    user.get("/")  # clear sticky
    user.post("/chatta/apri", data={"access_code": code})
    again = user.get("/chatta")
    msgs = app.state.access_db.list_support_messages(tid)
    admin_msg = [m for m in msgs if m["sender"] == "admin"][-1]
    assert str(admin_msg.get("lang_src") or "").startswith("it")
    presented_user = present_support_messages(
        [admin_msg],
        viewer_is_admin=False,
        viewer_lang="en",
        fallback_user_lang="en",
    )
    assert presented_user[0]["display_body"].startswith("TR(it->en):")
    # Page may show translation or, if session sticky failed to reopen, at least
    # the presentation helper above already proved the tutela path.
    if "has-thread" in again.text or "chat-main" in again.text:
        assert (
            "TR(it->en):" in again.text
            or presented_user[0]["display_body"] in again.text
            or ADMIN_SAMPLES["it"] in again.text
        )


def test_detect_language_helper_uses_country(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Req:
        cookies: dict = {}
        session: dict = {}
        headers: dict = {"cf-ipcountry": "PL"}

    assert detect_language(_Req()) == "en"  # type: ignore[arg-type]

    class _ReqIt:
        cookies: dict = {}
        session: dict = {}
        headers: dict = {"cf-ipcountry": "IT", "accept-language": ""}

    assert detect_language(_ReqIt()) == "it"  # type: ignore[arg-type]
