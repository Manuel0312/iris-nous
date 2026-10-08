"""Admin ban / hard-delete and chat auto-translate smoke tests."""

from __future__ import annotations

from pathlib import Path

import pytest
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


def test_ban_kicks_active_session_and_companion(tmp_path: Path) -> None:
    app = create_app(
        data_dir=tmp_path,
        session_secret="mod-kick-secret",
        admin_username="admin",
        admin_password="admin123",
    )
    store = app.state.store
    user = store.register(
        "onlineban",
        "headset-ban-2",
        password="Password1!",
        email="online.ban@example.com",
    )
    assert user is not None
    user.email_verified = True
    user.first_name = "Online"
    user.last_name = "Ban"
    user.gender = "non_binary"
    user.anagrafica_complete = True
    store.save(user)

    victim = TestClient(app)
    ok = victim.post(
        "/login",
        data={"username": user.username, "password": "Password1!"},
        follow_redirects=False,
    )
    assert ok.status_code in {200, 302, 303}
    dash = victim.get("/dashboard", follow_redirects=False)
    assert dash.status_code == 200

    profile, token = store.issue_companion_token(user.username)
    assert token
    assert (profile.usage_stats or {}).get("companion_device_token")

    admin = TestClient(app)
    admin.post("/login", data={"username": "admin", "password": "admin123"})
    banned = admin.post(
        f"/accessi/utente/{user.username}/ban",
        data={"duration": "1d"},
        follow_redirects=False,
    )
    assert banned.status_code in {302, 303}
    assert store.ban_status(user.username)["active"] is True
    refreshed = store.get(user.username)
    assert refreshed is not None
    assert not (refreshed.usage_stats or {}).get("companion_device_token")

    # Still logged in: first API hit must 403 + clear session (no wait for logout).
    api_kick = victim.post(
        "/api/phone/heartbeat",
        headers={"Accept": "application/json"},
    )
    assert api_kick.status_code == 403
    body = api_kick.json()
    assert body.get("banned") is True or "sospeso" in str(body.get("detail", "")).lower()

    kicked = victim.get("/dashboard", follow_redirects=False)
    assert kicked.status_code in {302, 303}
    assert "/login" in (kicked.headers.get("location") or "")

    companion = victim.post(
        "/api/companion/heartbeat",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    assert companion.status_code in {401, 403}

    gone = admin.post(f"/accessi/utente/{user.username}/elimina", follow_redirects=False)
    assert gone.status_code in {302, 303}
    assert store.get(user.username) is None
    assert store.db.get_user(user.username, include_deleted=True) is None


@pytest.mark.skip(reason="optional live network call; covered by unit present() test")
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
