"""Tre utenti «veri»: registrazione → anagrafica → cuffia → APK → squillo → In ascolto.

Simula tre persone distinte sullo stesso server (store isolato in tmp),
con stati indipendenti (chiamata / idle / musica).
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from bci_iot.pipeline.context_router import reset_context_router
from bci_iot.web import create_app

USERS = (
    {
        "username": "giulia_rossi",
        "password": "GiuliaPass1",
        "email": "giulia.rossi@gmail.com",
        "first_name": "Giulia",
        "last_name": "Rossi",
        "gender": "female",
        "phone": "3331112233",
        "label": "Pixel Giulia",
    },
    {
        "username": "marco_bianchi",
        "password": "MarcoPass1",
        "email": "marco.bianchi@gmail.com",
        "first_name": "Marco",
        "last_name": "Bianchi",
        "gender": "male",
        "phone": "3334445566",
        "label": "Samsung Marco",
    },
    {
        "username": "alex_verdi",
        "password": "AlexPass12",
        "email": "alex.verdi@gmail.com",
        "first_name": "Alex",
        "last_name": "Verdi",
        "gender": "non_binary",
        "phone": "3337778899",
        "label": "iPhone Alex",
    },
)


def _register_full(client: TestClient, store, u: dict) -> None:
    r = client.post(
        "/register",
        data={
            "username": u["username"],
            "email": u["email"],
            "password": u["password"],
        },
        follow_redirects=False,
    )
    assert r.status_code in {200, 302, 303}, r.text[:300]
    profile = store.get(u["username"])
    assert profile is not None
    profile.email_verified = True
    store.save(profile)
    r = client.post(
        "/anagrafica",
        data={
            "first_name": u["first_name"],
            "last_name": u["last_name"],
            "gender": u["gender"],
            "email": u["email"],
            "phone_country": "IT",
            "phone_national": u["phone"],
            "phone_label": u["label"],
        },
        follow_redirects=False,
    )
    assert r.status_code in {200, 302, 303}, r.text[:300]
    store.ensure_headset_pairing(u["username"])
    store.mark_calibration_complete(u["username"])


def _pair_apk(client: TestClient, store, u: dict) -> str:
    profile = store.ensure_headset_pairing(u["username"])
    pin = profile.pairing_code
    client.post("/api/auth/logout")
    pair = client.post(
        "/api/companion/pair",
        json={
            "username": u["username"],
            "password": u["password"],
            "code": pin,
        },
    )
    assert pair.status_code == 200, pair.text
    token = pair.json()["device_token"]
    assert token
    return token


def _login_web(client: TestClient, u: dict) -> None:
    client.post(
        "/login",
        data={"username": u["username"], "password": u["password"]},
        follow_redirects=False,
    )


def test_three_real_users_isolated_journeys(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="three-users")
    client = TestClient(app)
    store = app.state.store

    tokens: dict[str, str] = {}

    # 1) Ognuno completa onboarding + pairing APK
    for u in USERS:
        reset_context_router(u["username"])
        _register_full(client, store, u)
        tokens[u["username"]] = _pair_apk(client, store, u)
        beat = client.post(
            "/api/companion/heartbeat",
            headers={"Authorization": f"Bearer {tokens[u['username']]}"},
        )
        assert beat.status_code == 200
        body = beat.json()
        assert body["username"] == u["username"]
        assert body["phone_paired"] is True
        assert body["ecosystem"]["telefono"]["done"] is True
        assert body["calibration_complete"] is True

    # 2) Ecosistema: CTA post-setup (niente «Installa APK» / «Associa»)
    for u in USERS:
        _login_web(client, u)
        eco = client.get("/ecosistema")
        assert eco.status_code == 200
        assert "Apri cuffia" in eco.text or "Gestisci cuffia" in eco.text
        assert "Installa APK Android" not in eco.text
        assert "eco-download-qrs" in eco.text
        assert "Stato telefono" in eco.text
        assert "Associazione" in eco.text

    # 3) Eventi diversi per utente — non devono mescolarsi
    # Giulia: chiamata in arrivo
    g = USERS[0]
    r = client.post(
        "/api/companion/event",
        headers={"Authorization": f"Bearer {tokens[g['username']]}"},
        json={"event": "call_incoming", "caller": "Mamma"},
    )
    assert r.status_code == 200

    # Marco: musica
    m = USERS[1]
    r = client.post(
        "/api/companion/event",
        headers={"Authorization": f"Bearer {tokens[m['username']]}"},
        json={"event": "music_playing", "track": "Blinding Lights"},
    )
    assert r.status_code == 200

    # Alex: idle (nessun evento extra) — dopo clear esplicito
    a = USERS[2]
    r = client.post(
        "/api/companion/event",
        headers={"Authorization": f"Bearer {tokens[a['username']]}"},
        json={"event": "call_ended"},
    )
    assert r.status_code == 200

    # 4) Ogni utente sul PC vede solo il proprio contesto
    _login_web(client, g)
    st_g = client.get("/api/context/status").json()
    assert st_g["active_contexts"]["call"] is True
    assert st_g["world"]["incoming_call"] is True
    assert "Mamma" in (st_g["world"].get("caller_name") or "")

    _login_web(client, m)
    st_m = client.get("/api/context/status").json()
    assert st_m["active_contexts"]["music"] is True
    assert st_m["world"]["music_playing"] is True
    assert st_m["world"]["incoming_call"] is False

    _login_web(client, a)
    st_a = client.get("/api/context/status").json()
    assert st_a["active_contexts"]["call"] is False
    assert st_a["world"]["incoming_call"] is False

    # 5) Persistenza: reset RAM → hydrate da profilo (Giulia ancora in chiamata)
    reset_context_router(g["username"])
    _login_web(client, g)
    st_g2 = client.get("/api/context/status").json()
    assert st_g2["world"]["incoming_call"] is True

    # 6) Token di uno non agisce sull'altro
    bad = client.post(
        "/api/companion/event",
        headers={"Authorization": f"Bearer {tokens[m['username']]}"},
        json={"event": "call_incoming", "caller": "Intruso"},
    )
    assert bad.status_code == 200
    _login_web(client, g)
    still = client.get("/api/context/status").json()
    assert still["world"]["caller_name"] == "Mamma"
    _login_web(client, m)
    marco_call = client.get("/api/context/status").json()
    assert marco_call["world"]["incoming_call"] is True
    assert marco_call["world"]["caller_name"] == "Intruso"

    # 7) Pagine anti-confusione app
    android = client.get("/app/android")
    assert android.status_code == 200
    assert "IrisNous.apk" in android.text or "apk" in android.text.lower()


def test_three_users_ban_one_does_not_affect_others(tmp_path: Path) -> None:
    """Ban su un utente: gli altri APK continuano a fare heartbeat."""

    app = create_app(data_dir=tmp_path, session_secret="three-ban")
    client = TestClient(app)
    store = app.state.store

    tokens: dict[str, str] = {}
    for u in USERS:
        reset_context_router(u["username"])
        _register_full(client, store, u)
        tokens[u["username"]] = _pair_apk(client, store, u)

    banned = USERS[1]["username"]
    store.ban_user(banned, "7d")
    ban_status = store.ban_status(banned)
    assert ban_status.get("active") is True

    # Ban invalida anche il token companion → 401/403
    denied = client.post(
        "/api/companion/heartbeat",
        headers={"Authorization": f"Bearer {tokens[banned]}"},
    )
    assert denied.status_code in {401, 403}

    for u in USERS:
        if u["username"] == banned:
            continue
        ok = client.post(
            "/api/companion/heartbeat",
            headers={"Authorization": f"Bearer {tokens[u['username']]}"},
        )
        assert ok.status_code == 200, f"{u['username']}: {ok.text}"
