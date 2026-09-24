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


def test_fallback_user_lang_when_lang_src_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        "bci_iot.accounts.chat_translate.translate_text",
        lambda text, source, target: f"{source}->{target}:{text}",
    )
    messages = [
        {
            "sender": "user",
            "body": "Hello",
            "body_translated": "",
            "lang_src": "",
            "lang_dst": "",
        }
    ]
    shown = present_support_messages(
        messages,
        viewer_is_admin=True,
        viewer_lang="it",
        fallback_user_lang="en",
    )
    assert shown[0]["display_body"] == "en->it:Hello"
    assert shown[0]["show_original"] is True


def test_wrong_lang_src_still_translates_english_for_italian_admin() -> None:
    from bci_iot.accounts.chat_translate import present_support_messages

    shown = present_support_messages(
        [
            {
                "sender": "user",
                "body": "hi, I cannot associate the headphone",
                "body_translated": "",
                "lang_src": "it",
                "lang_dst": "",
            }
        ],
        viewer_is_admin=True,
        viewer_lang="it",
        fallback_user_lang="it",
    )
    assert shown[0]["show_original"] is True
    assert shown[0]["display_body"].lower() != "hi, i cannot associate the headphone"
    assert any(
        w in shown[0]["display_body"].lower()
        for w in ("cuffia", "auricolare", "associare", "cuffie")
    )


def test_hi_how_are_you_detected_english() -> None:
    from bci_iot.accounts.chat_translate import detect_message_language

    assert detect_message_language("hi how are you", hint="it") == "en"


def test_hi_how_are_you_translates_for_italian_admin() -> None:
    shown = present_support_messages(
        [
            {
                "sender": "user",
                "body": "hi how are you",
                "body_translated": "",
                "lang_src": "it",
                "lang_dst": "",
            }
        ],
        viewer_is_admin=True,
        viewer_lang="it",
        fallback_user_lang="en",
    )
    assert shown[0]["show_original"] is True
    low = shown[0]["display_body"].lower()
    assert low != "hi how are you"
    assert any(w in low for w in ("ciao", "come", "stai", "sta"))


def test_resolve_recipient_lang_from_english_message() -> None:
    from bci_iot.accounts.chat_translate import resolve_support_recipient_lang

    lang = resolve_support_recipient_lang(
        thread_user_lang="it",
        messages=[{"sender": "user", "body": "hi how are you"}],
    )
    assert lang == "en"


def test_support_reply_email_is_localized_english() -> None:
    from bci_iot.accounts.messaging import build_support_reply_email

    subject, text, html = build_support_reply_email(
        name="Manuel",
        body="Please check the headset pairing.",
        conversation=[
            {"sender": "user", "display_body": "hi how are you", "body": "hi how are you"},
        ],
        lang="en",
    )
    assert "reply to your message" in subject.lower()
    assert "Hi Manuel" in text or "Hi Manuel," in text
    assert "Please check the headset pairing." in text
    assert "Risposta del team" not in text
    assert "Conversazione" not in text
    assert 'lang="en"' in html



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
