"""Send one Iris Nous email via Gmail SMTP. Used by GitHub Actions."""

from __future__ import annotations

import html as html_lib
import json
import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from pathlib import Path


def _load_payload() -> dict[str, str]:
    path = (os.environ.get("MAIL_FILE") or "").strip()
    if path and Path(path).is_file():
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {str(k): "" if v is None else str(v) for k, v in data.items()}
    return {
        "to": os.environ.get("MAIL_TO") or "",
        "subject": os.environ.get("MAIL_SUBJECT") or "",
        "text": os.environ.get("MAIL_TEXT") or "",
        "html": os.environ.get("MAIL_HTML") or "",
    }


def _html_from_text(text: str) -> str:
    safe = html_lib.escape(text or "Iris Nous").replace("\n", "<br />\n")
    return (
        "<html><body style='font-family:-apple-system,Segoe UI,Helvetica,Arial,"
        "sans-serif;color:#1d1d1f;line-height:1.5'>"
        f"<p>{safe}</p></body></html>"
    )


def main() -> int:
    payload = _load_payload()
    user = (os.environ.get("SMTP_USER") or "").strip()
    password = (os.environ.get("SMTP_PASSWORD") or "").strip()
    from_addr = (os.environ.get("SMTP_FROM") or user).strip()
    to_addr = (payload.get("to") or "").strip()
    subject = (payload.get("subject") or "Iris Nous").strip() or "Iris Nous"
    text = payload.get("text") or ""
    html = payload.get("html") or ""
    if not (user and password and from_addr and to_addr):
        raise SystemExit("missing mail secrets or destination")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr(("Iris Nous", from_addr))
    msg["To"] = to_addr
    msg["Reply-To"] = from_addr
    msg["Date"] = formatdate(localtime=False)
    msg["Message-ID"] = make_msgid(domain="gmail.com")
    msg["X-Mailer"] = "Iris Nous"
    msg.set_content(text or "Iris Nous")
    msg.add_alternative(html or _html_from_text(text), subtype="html")

    context = ssl.create_default_context()
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as smtp:
        smtp.ehlo()
        smtp.starttls(context=context)
        smtp.ehlo()
        smtp.login(user, password)
        smtp.send_message(msg)
    print("sent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
