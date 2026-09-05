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


def test_chatta_and_admin_inbox_flow(tmp_path: Path) -> None:
    app = create_app(
        data_dir=tmp_path,
        session_secret="support-secret",
        admin_username="admin",
        admin_password="admin123",
    )
    client = TestClient(app)
    guest = client.post(
        "/chatta",
        data={
            "channel": "email",
            "name": "Luca Bianchi",
            "email": "luca@gmail.com",
            "phone": "3339998877",
            "subject": "Spotify",
            "body": "Non parte Spotify dal telefono, come lo collego?",
        },
        follow_redirects=False,
    )
    assert guest.status_code == 303

    denied = client.get("/notifiche", follow_redirects=False)
    assert denied.status_code == 303

    client.post("/login", data={"username": "admin", "password": "admin123"})
    inbox = client.get("/notifiche")
    assert inbox.status_code == 200
    assert "Non visualizzato" in inbox.text
    assert "status-unread" in inbox.text
    assert "Luca Bianchi" in inbox.text

    thread_id = app.state.access_db.list_support_threads()[0]["id"]
    opened = client.get(f"/notifiche/{thread_id}")
    assert opened.status_code == 200
    assert "Visto, non risposto" in opened.text or "Visualizzato" in opened.text

    reply = client.post(
        f"/notifiche/{thread_id}/rispondi",
        data={"body": "Ciao Luca, apri Associa telefono e ricollega Spotify."},
        follow_redirects=False,
    )
    assert reply.status_code == 303
    done = client.get("/notifiche")
    assert "Risposto" in done.text
    assert "status-replied" in done.text
    assert "iris-bg" in client.get("/").text
    assert "bg3d.js" in client.get("/login").text
    assert "page-private" in client.get("/notifiche").text
    assert 'class="chat-fab"' not in client.get("/accessi").text
    assert "Mail Iris Nous" not in client.get("/accessi").text
    assert "Contattaci" not in client.get("/accessi").text
    chat_admin = client.get("/chatta", follow_redirects=False)
    assert chat_admin.status_code in {302, 303}
    assert "/notifiche" in chat_admin.headers.get("location", "")
    guest_chat = TestClient(app).get("/chatta")
    assert "Chi sei" in guest_chat.text
    assert "ai-chat" in guest_chat.text
    assert "Agente AI" in guest_chat.text
    assert "contatto telefonico" in guest_chat.text
    mail = TestClient(app).get("/chatta?canale=email")
    assert "contact-mail" in mail.text
    assert "Contattaci" in mail.text
    accessi = client.get("/accessi?q=luca@gmail.com")
    assert accessi.status_code == 200
