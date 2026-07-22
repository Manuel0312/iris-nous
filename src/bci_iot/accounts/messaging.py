"""Deliver verification / recovery codes (SMTP, Twilio, or demo fallback)."""

from __future__ import annotations

import os
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Literal
from urllib import error, parse, request


Channel = Literal["email", "phone"]


@dataclass(frozen=True, slots=True)
class DeliveryResult:
    ok: bool
    channel: Channel
    destination: str
    mode: Literal["smtp", "twilio", "demo"]
    detail: str = ""
    demo_code: str = ""


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def send_code(
    *,
    channel: Channel,
    destination: str,
    code: str,
    purpose: str,
) -> DeliveryResult:
    """Send a 6-digit code. Falls back to demo mode when providers are unset."""
    label = {
        "verify_email": "verifica email",
        "verify_phone": "verifica telefono",
        "recover": "recupero password",
    }.get(purpose, "Iris Nous")
    body = f"Il tuo codice Iris Nous ({label}) è: {code}. Scade tra 15 minuti."

    if channel == "email":
        smtp = _try_smtp(destination, subject=f"Codice Iris Nous — {label}", body=body)
        if smtp is not None:
            return smtp
    else:
        sms = _try_twilio(destination, body=body)
        if sms is not None:
            return sms

    return DeliveryResult(
        ok=True,
        channel=channel,
        destination=destination,
        mode="demo",
        detail=(
            "Invio reale non configurato: in questa installazione il codice "
            "viene mostrato a schermo (modalità demo / tesi)."
        ),
        demo_code=code,
    )


def _try_smtp(to_addr: str, *, subject: str, body: str) -> DeliveryResult | None:
    host = _env("BCI_IOT_SMTP_HOST")
    user = _env("BCI_IOT_SMTP_USER")
    password = _env("BCI_IOT_SMTP_PASSWORD")
    from_addr = _env("BCI_IOT_SMTP_FROM") or user
    if not host or not from_addr:
        return None
    port = int(_env("BCI_IOT_SMTP_PORT") or "587")
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.set_content(body)
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            smtp.starttls(context=context)
            if user and password:
                smtp.login(user, password)
            smtp.send_message(msg)
    except (OSError, smtplib.SMTPException) as exc:
        return DeliveryResult(
            ok=False,
            channel="email",
            destination=to_addr,
            mode="smtp",
            detail=f"Invio email non riuscito: {exc}",
        )
    return DeliveryResult(
        ok=True,
        channel="email",
        destination=to_addr,
        mode="smtp",
        detail="Codice inviato via email.",
    )


def _try_twilio(to_e164: str, *, body: str) -> DeliveryResult | None:
    sid = _env("BCI_IOT_TWILIO_ACCOUNT_SID")
    token = _env("BCI_IOT_TWILIO_AUTH_TOKEN")
    from_num = _env("BCI_IOT_TWILIO_FROM")
    if not sid or not token or not from_num:
        return None
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    data = parse.urlencode({"To": to_e164, "From": from_num, "Body": body}).encode()
    req = request.Request(url, data=data, method="POST")
    import base64

    auth = base64.b64encode(f"{sid}:{token}".encode()).decode()
    req.add_header("Authorization", f"Basic {auth}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with request.urlopen(req, timeout=20) as resp:
            if resp.status >= 400:
                return DeliveryResult(
                    ok=False,
                    channel="phone",
                    destination=to_e164,
                    mode="twilio",
                    detail=f"Invio SMS non riuscito (HTTP {resp.status}).",
                )
    except error.URLError as exc:
        return DeliveryResult(
            ok=False,
            channel="phone",
            destination=to_e164,
            mode="twilio",
            detail=f"Invio SMS non riuscito: {exc}",
        )
    return DeliveryResult(
        ok=True,
        channel="phone",
        destination=to_e164,
        mode="twilio",
        detail="Codice inviato via SMS.",
    )
