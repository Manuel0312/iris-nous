"""Quick OTP / recover regression checks."""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from bci_iot.accounts.messaging import configure_messaging_store, send_code
from bci_iot.accounts.otp import (
    generate_otp_code,
    hash_otp,
    normalize_otp,
    otp_binding_salt,
    otp_matches,
)
from bci_iot.web import create_app


def main() -> None:
    c = generate_otp_code()
    assert len(c) == 6 and c.isalnum() and " " not in c
    assert normalize_otp(" a3 k9 p2 ") == "A3K9P2"
    salt = otp_binding_salt(user_id="u1", purpose="recover", channel="email")
    h = hash_otp(c, salt=salt)
    assert otp_matches(c, stored_hash=h, salt=salt)
    assert otp_matches(c.lower() + " ", stored_hash=h, salt=salt)
    assert not otp_matches(c, stored_hash=h, salt="other")
    print("otp ok", c)

    os.environ["BCI_IOT_OTP_DEMO"] = "1"
    for key in list(os.environ):
        if "SMTP" in key or "TWILIO" in key:
            os.environ.pop(key, None)

    tmp = Path("data/_qa_otp_fix")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)

    app = create_app(data_dir=tmp, session_secret="x")
    client = TestClient(app)
    r = client.post(
        "/register",
        data={"username": "u1", "email": "u1@gmail.com", "password": "Segreta123"},
        follow_redirects=False,
    )
    assert r.status_code in (200, 302, 303)
    client.post(
        "/anagrafica",
        data={
            "first_name": "A",
            "last_name": "B",
            "gender": "female",
            "email": "u1@gmail.com",
            "phone_country": "IT",
            "phone_national": "3331234567",
            "phone_label": "",
        },
    )
    client.post("/api/auth/logout")
    r = client.post(
        "/recupera-password",
        data={"action": "identify", "identifier": "u1@gmail.com", "channel": "email"},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    page = client.get("/recupera-password")
    assert "A3K9P2" in page.text
    assert 'inputmode="numeric"' not in page.text
    m = re.search(r"([A-Z0-9]{6})", page.text)
    assert m, page.text[:800]
    code = m.group(1)
    r = client.post(
        "/recupera-password",
        data={
            "action": "confirm",
            "code": f" {code.lower()} ",
            "new_password": "NuovaSegreta1",
            "new_password2": "NuovaSegreta1",
        },
        follow_redirects=False,
    )
    assert r.status_code in (302, 303), r.headers
    r = client.post(
        "/login",
        data={"username": "u1", "password": "NuovaSegreta1"},
        follow_redirects=False,
    )
    assert r.status_code in (200, 302, 303)
    print("recover with alphanumeric + spaces stripped: ok")

    os.environ.pop("BCI_IOT_OTP_DEMO", None)
    os.environ.pop("BCI_IOT_REQUIRE_REAL_OTP", None)
    os.environ["BCI_IOT_ENV"] = "dev"
    configure_messaging_store(tmp)
    res = send_code(
        channel="email", destination="a@b.com", code="ABCDEF", purpose="recover"
    )
    assert res.ok is True and res.mode == "demo" and res.demo_code == "ABCDEF", res
    print("default demo send ok")
    print("ALL GOOD")


if __name__ == "__main__":
    main()
