"""Admin people search, support inbox, and tutela chat."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from bci_iot.accounts.access_db import AccessDatabase
from bci_iot.web import create_app


def test_admin_search_by_email_and_phone(tmp_path: Path) -> None:
    db = AccessDatabase(tmp_path / "t.db")
    db.upsert_anagrafica(
        username="maria",
        user_id="u1",
        first_name="Maria",
        last_name="Rossi",
        gender="female",
        email="maria@gmail.com",
        phone_e164="+393331234567",
        phone_label="iPhone",
    )
    db.upsert_user(
        {
            "username": "maria",
            "password_hash": "x",
            "user_id": "u1",
            "email": "maria@gmail.com",
            "phone_e164": "+393331234567",
            "phone_national": "3331234567",
            "phone_label": "iPhone",
            "first_name": "Maria",
            "last_name": "Rossi",
        }
    )
    by_email = db.list_people(q="maria@gmail.com")
    assert [p.username for p in by_email] == ["maria"]
    by_phone = db.list_people(q="3331234567")
    assert [p.username for p in by_phone] == ["maria"]
    by_e164 = db.list_people(q="+39 333 123 4567")
    assert [p.username for p in by_e164] == ["maria"]
    assert db.list_people(q="inesistente") == []


def test_support_status_dots_and_tutela_archive(tmp_path: Path) -> None:
    db = AccessDatabase(tmp_path / "t.db")
    thread_id = db.add_user_support_message(
        username="maria",
        guest_name="Maria Rossi",
        guest_email="maria@gmail.com",
        guest_phone="+393331234567",
        channel="chat",
        subject="Aiuto cuffia",
        body="Non si collega la cuffia, potete aiutarmi?",
    )
    thread = db.get_support_thread(thread_id)
    assert thread is not None
    assert thread["status"] == "unread"
    assert db.support_unread_count() == 1

    db.mark_support_viewed(thread_id)
    viewed = db.get_support_thread(thread_id)
    assert viewed is not None
    assert viewed["status"] == "viewed"
    assert db.support_unread_count() == 0

    db.add_admin_support_reply(thread_id, "Ciao Maria, controlla l'associazione telefono.")
    replied = db.get_support_thread(thread_id)
    assert replied is not None
    assert replied["status"] == "replied"
    assert db.list_support_threads()
    assert db.list_user_support_threads(username="maria")

    old = (datetime.now(timezone.utc) - timedelta(days=11)).replace(microsecond=0).isoformat()
    with db._connect() as conn:
        conn.execute(
            "UPDATE support_threads SET replied_at = ? WHERE id = ?",
            (old, thread_id),
        )
        conn.commit()
    db.hide_expired_inbox()
    assert db.list_support_threads() == []
    archive = db.list_support_threads(archive=True)
    assert len(archive) == 1
    tutela = db.list_user_support_threads(username="maria", email="maria@gmail.com")
    assert len(tutela) == 1
    messages = db.list_support_messages(thread_id)
    assert [m["sender"] for m in messages] == ["user", "admin"]


def test_chatta_and_admin_inbox_flow(tmp_path: Path, monkeypatch) -> None:
    from bci_iot.accounts.messaging import DeliveryResult
    import importlib

    sent: dict[str, str] = {}

    def fake_send(**kwargs):
        sent["destination"] = str(kwargs.get("destination") or "")
        sent["subject"] = str(kwargs.get("subject") or "")
        sent["text"] = str(kwargs.get("text") or "")
        return DeliveryResult(
            ok=True,
            channel="email",
            destination=sent["destination"],
            mode="smtp",
            detail="ok",
        )

    webapp = importlib.import_module("bci_iot.web.app")
    monkeypatch.setattr(webapp, "send_branded_email", fake_send)
    app = create_app(
        data_dir=tmp_path,
        session_secret="support-secret",
        admin_username="admin",
        admin_password="admin123",
    )
    guest = TestClient(app)
    posted = guest.post(
        "/chatta",
        data={
            "name": "Luca Bianchi",
            "email": "luca@gmail.com",
            "phone": "3339998877",
            "body": "Non parte Spotify dal telefono, come lo collego?",
        },
        follow_redirects=False,
    )
    assert posted.status_code == 200
    thread_page = guest.get("/chatta")
    assert thread_page.status_code == 200
    assert "contact-modes" not in thread_page.text
    assert "canale=email" not in thread_page.text
    assert "Non parte Spotify" in thread_page.text
    assert "Descrivi il problema" in thread_page.text

    denied = guest.get("/notifiche", follow_redirects=False)
    assert denied.status_code == 303

    admin = TestClient(app)
    admin.post("/login", data={"username": "admin", "password": "admin123"})
    inbox = admin.get("/notifiche")
    assert inbox.status_code == 200
    assert "Non visualizzato" in inbox.text
    assert "status-unread" in inbox.text
    assert "Luca Bianchi" in inbox.text

    thread_id = app.state.access_db.list_support_threads()[0]["id"]
    opened = admin.get(f"/notifiche/{thread_id}")
    assert opened.status_code == 200
    assert "Visto, non risposto" in opened.text or "Visualizzato" in opened.text

    reply = admin.post(
        f"/notifiche/{thread_id}/rispondi",
        data={"body": "Ciao Luca, apri Associa telefono e ricollega Spotify."},
        follow_redirects=False,
    )
    assert reply.status_code == 200
    assert sent.get("destination") == "luca@gmail.com"
    assert "Non parte Spotify" in sent.get("text", "")
    assert "Ciao Luca, apri Associa telefono" in sent.get("text", "")
    done = admin.get("/notifiche")
    assert "Risposto" in done.text
    assert "status-replied" in done.text
    answered = guest.get("/chatta")
    assert "Ciao Luca, apri Associa telefono" in answered.text
    code = str(app.state.access_db.list_support_threads()[0].get("access_code") or "")
    assert len(code) == 6
    other_device = TestClient(app)
    other_device.post("/chatta/apri", data={"access_code": code})
    recovered = other_device.get("/chatta")
    assert "Ciao Luca, apri Associa telefono" in recovered.text
    assert "iris-bg" in admin.get("/").text
    assert "bg3d.js" in admin.get("/login").text
    assert "page-private" in admin.get("/notifiche").text
    assert 'class="chat-fab"' not in admin.get("/accessi").text
    assert "Mail Iris Nous" not in admin.get("/accessi").text
    assert "Contattaci" not in admin.get("/accessi").text
    chat_admin = admin.get("/chatta", follow_redirects=False)
    assert chat_admin.status_code in {302, 303}
    assert "/notifiche" in chat_admin.headers.get("location", "")
    guest_chat = TestClient(app).get("/chatta")
    assert "Richiesta di chat" in guest_chat.text
    assert "Spiegaci il problema" in guest_chat.text
    assert "Solo tu e il team Iris" not in guest_chat.text
    assert "La conversazione compare qui al centro" not in guest_chat.text
    assert "chat-disclaimer-full" in guest_chat.text
    assert "Ti rispondiamo di persona" not in guest_chat.text
    assert "Hai già scritto da un altro telefono" not in guest_chat.text
    assert "Agente AI" not in guest_chat.text
    assert "ai-chat" not in guest_chat.text
    assert "contact-modes" not in guest_chat.text
    assert "Contattaci" not in guest_chat.text
    assert "Codice chat" in guest_chat.text
    assert "chat-split" in guest_chat.text
    assert "has-thread" not in guest_chat.text
    assert "chat-main" not in guest_chat.text
    mail = TestClient(app).get("/chatta?canale=email")
    assert "contact-mail" in mail.text
    assert "contact-modes" not in mail.text
    assert "Contattaci" not in mail.text
    accessi = admin.get("/accessi?q=luca@gmail.com")
    assert accessi.status_code == 200


def test_resend_from_header_skips_gmail() -> None:
    from bci_iot.accounts.messaging import RESEND_TEST_FROM, _resend_from_header

    header = _resend_from_header(
        {
            "brand_from_email": "noreply.irisnous@gmail.com",
            "smtp_from": "noreply.irisnous@gmail.com",
        }
    )
    assert header == RESEND_TEST_FROM
    assert "onboarding@resend.dev" in header


def test_resend_request_includes_user_agent(monkeypatch) -> None:
    from bci_iot.accounts import messaging as messaging_mod

    captured: dict[str, str] = {}

    class _Resp:
        status = 200

        def read(self) -> bytes:
            return b'{"id":"re_test"}'

        def __enter__(self):
            return self

        def __exit__(self, *args) -> bool:
            return False

    def fake_urlopen(req, timeout=20):
        captured.update({k.lower(): v for k, v in req.header_items()})
        return _Resp()

    monkeypatch.setenv("BCI_IOT_RESEND_API_KEY", "re_test_key")
    monkeypatch.setenv("BCI_IOT_RESEND_FROM", "Iris Nous <mail@irisnous.test>")
    monkeypatch.setattr(messaging_mod.request, "urlopen", fake_urlopen)
    result = messaging_mod._try_resend(
        "manu@example.com",
        subject="Iris Nous: conferma iscrizione",
        text="ciao",
        html="<p>ciao</p>",
    )
    assert result is not None and result.ok
    assert "user-agent" in captured
    assert "IrisNous" in captured["user-agent"]


def test_resend_skipped_when_from_would_be_onboarding(monkeypatch) -> None:
    from bci_iot.accounts import messaging as messaging_mod

    monkeypatch.setenv("BCI_IOT_RESEND_API_KEY", "re_test_key")
    monkeypatch.delenv("BCI_IOT_RESEND_FROM", raising=False)
    monkeypatch.setenv("BCI_IOT_SMTP_FROM", "noreply.irisnous@gmail.com")
    monkeypatch.setenv("BCI_IOT_MAIL_FROM", "noreply.irisnous@gmail.com")
    assert (
        messaging_mod._try_resend(
            "ve@gmail.com",
            subject="s",
            text="t",
            html="<p>t</p>",
        )
        is None
    )


def test_brevo_sends_from_iris_gmail(monkeypatch) -> None:
    import json

    from bci_iot.accounts import messaging as messaging_mod

    captured: dict[str, object] = {}

    class _Resp:
        status = 201

        def read(self) -> bytes:
            return b'{"messageId":"abc"}'

        def __enter__(self):
            return self

        def __exit__(self, *args) -> bool:
            return False

    def fake_urlopen(req, timeout=20):
        captured["body"] = json.loads(req.data.decode("utf-8"))
        captured["headers"] = {k.lower(): v for k, v in req.header_items()}
        return _Resp()

    monkeypatch.setenv("BCI_IOT_BREVO_API_KEY", "xkeysib-test")
    monkeypatch.setenv("BCI_IOT_SMTP_FROM", "noreply.irisnous@gmail.com")
    monkeypatch.setattr(messaging_mod.request, "urlopen", fake_urlopen)
    result = messaging_mod._try_brevo(
        "ve@gmail.com",
        subject="Conferma la tua iscrizione a Iris Nous",
        text="codice ABC123",
        html="<p>ABC123</p>",
    )
    assert result is not None and result.ok
    body = captured["body"]
    assert isinstance(body, dict)
    assert body["sender"]["email"] == "noreply.irisnous@gmail.com"
    assert "ABC123" in body["textContent"]
    headers = captured["headers"]
    assert isinstance(headers, dict)
    assert "IrisNous" in str(headers.get("user-agent") or "")


def test_github_relay_posts_dispatch(monkeypatch) -> None:
    from bci_iot.accounts import messaging as messaging_mod

    captured: dict[str, object] = {}

    def fake_http(url, payload, extra_headers, timeout=20):
        captured["url"] = url
        captured["payload"] = payload
        captured["headers"] = extra_headers
        return 204, ""

    monkeypatch.setenv("BCI_IOT_GITHUB_MAIL_TOKEN", "ghs_test")
    monkeypatch.setenv("BCI_IOT_GITHUB_MAIL_REPO", "Manuel0312/iris-nous")
    monkeypatch.setattr(messaging_mod, "_http_post_json", fake_http)
    result = messaging_mod._try_github_relay(
        "ve@gmail.com",
        subject="Conferma la tua iscrizione a Iris Nous",
        text="Il tuo codice è ABCD12",
        html="<p>ABCD12</p>",
    )
    assert result is not None and result.ok
    assert result.mode == "github"
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["event_type"] == "iris-mail"
    body = payload["client_payload"]
    assert body["to"] == "ve@gmail.com"
    assert "ABCD12" in body["text"]
    headers = captured["headers"]
    assert isinstance(headers, dict)
    assert "Bearer ghs_test" in str(headers.get("Authorization") or "")
