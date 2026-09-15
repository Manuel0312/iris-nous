"""Tests for support-chat presentation / tutela translation rules."""

from __future__ import annotations

from bci_iot.accounts.chat_translate import present_support_messages


def test_author_always_sees_original_body() -> None:
    messages = [
        {
            "sender": "user",
            "body": "ciao",
            "body_translated": "hello",
            "lang_src": "it",
            "lang_dst": "en",
        }
    ]
    shown = present_support_messages(messages, viewer_is_admin=False, viewer_lang="en")
    assert shown[0]["display_body"] == "ciao"
    assert shown[0]["show_original"] is False


def test_admin_sees_own_reply_untranslated() -> None:
    messages = [
        {
            "sender": "admin",
            "body": "Guten Tag",
            "body_translated": "Buongiorno",
            "lang_src": "de",
            "lang_dst": "it",
        }
    ]
    shown = present_support_messages(messages, viewer_is_admin=True, viewer_lang="it")
    assert shown[0]["display_body"] == "Guten Tag"
    assert shown[0]["show_original"] is False


def test_recipient_uses_stored_translation_when_lang_matches(monkeypatch) -> None:
    called = {"n": 0}

    def _boom(*_a, **_k):
        called["n"] += 1
        raise AssertionError("should use stored translation")

    monkeypatch.setattr("bci_iot.accounts.chat_translate.translate_text", _boom)
    messages = [
        {
            "sender": "admin",
            "body": "Hallo",
            "body_translated": "Ciao",
            "lang_src": "de",
            "lang_dst": "it",
        }
    ]
    shown = present_support_messages(messages, viewer_is_admin=False, viewer_lang="it")
    assert shown[0]["display_body"] == "Ciao"
    assert shown[0]["show_original"] is True
    assert shown[0]["original_body"] == "Hallo"
    assert called["n"] == 0


def test_gap_catalog_covers_home_and_chatta_keys() -> None:
    from bci_iot.web.translations import CATALOG

    keys = (
        "Sintonizzati sul tuo spazio",
        "Spiegaci il problema.",
        "Riapri la chat",
        "Testo originale",
        "Connessione continua",
    )
    for lang in ("en", "es", "fr", "de", "pt", "zh", "ja"):
        for key in keys:
            assert key in CATALOG[lang], f"missing {lang}: {key}"
            assert CATALOG[lang][key].strip()
