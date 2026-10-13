from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from bci_iot.web.app import create_app


def test_factory_reset_keeps_admin_only(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="wipe-secret")
    client = TestClient(app)
    store = app.state.store

    store.create_account("wipe_me", "Segreta123", email="wipe@gmail.com")
    assert store.get("wipe_me") is not None

    login = client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=False,
    )
    assert login.status_code in {200, 302, 303}

    res = client.post("/api/admin/factory-reset-users")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "ok"
    assert "wipe_me" in body["removed"]
    assert store.get("wipe_me") is None
    assert store.get("admin") is not None
