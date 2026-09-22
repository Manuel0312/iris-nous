"""Admin ban / hard-delete and chat auto-translate smoke tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from bci_iot.accounts.chat_translate import present_support_messages, translate_text
from bci_iot.web import create_app


def test_admin_ban_and_hard_delete(tmp_path: Path) -> None:
    app = create_app(
        data_dir=tmp_path,
        session_secret="mod-secret",
        admin_username="admin",
        admin_password="admin123",
    )
    store = app.state.store
    user = store.register(
        "bannedguy",
        "headset-ban-1",
        password="Password1!",
        email="banned.guy@example.com",
    )
    assert user is not None

    admin = TestClient(app)
    admin.post("/login", data={"username": "admin", "password": "admin123"})
    page = admin.get(f"/accessi/utente/{user.username}")
    assert page.status_code == 200
    assert "Ban 1 giorno" in page.text or "Moderazione" in page.text

    banned = admin.post(
        f"/accessi/utente/{user.username}/ban",
        data={"duration": "3d"},
        follow_redirects=False,
    )
    assert banned.status_code in {302, 303}
    status = store.ban_status(user.username)
    assert status["active"] is True

    victim = TestClient(app)
    denied = victim.post(
        "/login",
        data={"username": user.username, "password": "Password1!"},
        follow_redirects=False,
    )
    assert denied.status_code == 200
    assert "sospeso" in denied.text.lower() or "Account sospeso" in denied.text

    admin.post(f"/accessi/utente/{user.username}/sblocca")
    assert store.ban_status(user.username)["active"] is False

    gone = admin.post(f"/accessi/utente/{user.username}/elimina", follow_redirects=False)
    assert gone.status_code in {302, 303}
    assert store.get(user.username) is None
    assert store.db.get_user(user.username, include_deleted=True) is None


def test_live_translate_en_to_it() -> None:
    out = translate_text(
        "I cannot associate the headphone",
        source="en",
        target="it",
    )
    assert out != "I cannot associate the headphone"
    assert any(w in out.lower() for w in ("cuffia", "auricolare", "associare", "cuffie", "non"))


def test_present_translates_for_admin_it(monkeypatch) -> None:
    monkeypatch.setattr(
        "bci_iot.accounts.chat_translate.translate_text",
        lambda text, source, target: f"{source}->{target}:{text}",
    )
    shown = present_support_messages(
        [
            {
                "sender": "user",
                "body": "Je n'arrive pas à associer le casque",
                "body_translated": "",
                "lang_src": "fr",
                "lang_dst": "",
            }
        ],
        viewer_is_admin=True,
        viewer_lang="it",
        fallback_user_lang="fr",
    )
    assert shown[0]["display_body"].startswith("fr->it:")
    assert shown[0]["show_original"] is True
