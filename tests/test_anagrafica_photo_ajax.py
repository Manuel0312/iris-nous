"""Photo upload keeps the anagrafica form in place (JSON, no forced reload)."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient

from bci_iot.web import create_app


def _login_new(client: TestClient, store, name: str = "foto_u") -> None:
    client.post(
        "/register",
        data={"username": name, "email": f"{name}@gmail.com", "password": "FotoPass1"},
        follow_redirects=False,
    )
    p = store.get(name)
    assert p is not None
    p.email_verified = True
    store.save(p)


def test_photo_upload_json_no_redirect_wipes(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="foto-ajax")
    client = TestClient(app)
    _login_new(client, app.state.store)
    # Tiny valid JPEG (1x1)
    jpeg = (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
        b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
        b"\x1f\x1e\x1d\x1a\x1c\x1c $.\' \",#\x1c\x1c(7),01444\x1f\'9=82<.342"
        b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
        b"\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b"
        b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xaa\xff\xd9"
    )
    res = client.post(
        "/anagrafica/foto",
        files={"photo": ("avatar.jpg", BytesIO(jpeg), "image/jpeg")},
        headers={"Accept": "application/json"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "ok"
    assert body["url"].startswith("/media/photos/")
    page = client.get("/anagrafica")
    assert page.status_code == 200
    assert "photo-change-btn" in page.text or "Cambia foto" in page.text
    assert "chat-fab" not in page.text or 'class="chat-fab"' not in page.text


def test_register_hides_chat_fab(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="no-fab")
    page = TestClient(app).get("/register")
    assert page.status_code == 200
    assert "chat-fab" not in page.text
