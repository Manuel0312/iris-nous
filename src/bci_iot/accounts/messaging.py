"""Deliver Iris Nous branded email (signup confirm, recovery codes).

SMS intentionally unused for password recovery.
Order: Resend → SMTP → local demo (dev).
"""

from __future__ import annotations

import json
import os
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path
from typing import Any, Literal
from urllib import error, request


Channel = Literal["email", "phone"]

_CONFIG_PATH: Path | None = None
_DOTENV_LOADED = False

BRAND_NAME = "Iris Nous"
DEFAULT_FROM_EMAIL = "noreply@iris-nous.app"
SUPPORT_LINE = "Questa è una mail automatica di Iris Nous. Non rispondere a questo indirizzo."


@dataclass(frozen=True, slots=True)
class DeliveryResult:
    ok: bool
    channel: Channel
    destination: str
    mode: Literal["resend", "smtp", "demo"]
    detail: str = ""
    demo_code: str = ""
    demo_link: str = ""


def configure_messaging_store(data_root: Path | str) -> Path:
    global _CONFIG_PATH
    root = Path(data_root)
    root.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH = root / "messaging.json"
    return _CONFIG_PATH


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_dotenv_file(path: Path | None = None) -> None:
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return
    _DOTENV_LOADED = True
    env_path = path or (_project_root() / ".env")
    if not env_path.is_file():
        return
    try:
        text = env_path.read_text(encoding="utf-8")
    except OSError:
        return
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def _env(name: str) -> str:
    load_dotenv_file()
    return (os.environ.get(name) or "").strip()


def _file_config() -> dict[str, Any]:
    path = _CONFIG_PATH
    if path is None or not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_messaging_config(values: dict[str, str]) -> Path:
    if _CONFIG_PATH is None:
        configure_messaging_store(_project_root() / "data")
    assert _CONFIG_PATH is not None
    current = _file_config()
    for key, value in values.items():
        cleaned = (value or "").strip()
        if cleaned:
            current[key] = cleaned
    _CONFIG_PATH.write_text(json.dumps(current, indent=2), encoding="utf-8")
    return _CONFIG_PATH


def update_messaging_config(
    *,
    brand_from_email: str | None = None,
    resend_api_key: str | None = None,
    smtp_host: str | None = None,
    smtp_port: str | None = None,
    smtp_user: str | None = None,
    smtp_password: str | None = None,
    smtp_from: str | None = None,
) -> Path:
    payload: dict[str, str] = {}
    mapping = {
        "brand_from_email": brand_from_email,
        "resend_api_key": resend_api_key,
        "smtp_host": smtp_host,
        "smtp_port": smtp_port,
        "smtp_user": smtp_user,
        "smtp_password": smtp_password,
        "smtp_from": smtp_from,
    }
    for key, value in mapping.items():
        if value is None:
            continue
        cleaned = value.strip()
        if cleaned:
            payload[key] = cleaned
    return save_messaging_config(payload)


def _merged_settings() -> dict[str, str]:
    file_cfg = _file_config()
    smtp_from = (
        _env("BCI_IOT_SMTP_FROM")
        or str(file_cfg.get("smtp_from") or "")
        or _env("BCI_IOT_SMTP_USER")
        or str(file_cfg.get("smtp_user") or "")
    )
    brand_from = (
        _env("BCI_IOT_MAIL_FROM")
        or str(file_cfg.get("brand_from_email") or "")
        or smtp_from
        or DEFAULT_FROM_EMAIL
    )
    return {
        "brand_from_email": brand_from,
        "resend_api_key": _env("BCI_IOT_RESEND_API_KEY")
        or str(file_cfg.get("resend_api_key") or ""),
        "smtp_host": _env("BCI_IOT_SMTP_HOST") or str(file_cfg.get("smtp_host") or ""),
        "smtp_port": _env("BCI_IOT_SMTP_PORT") or str(file_cfg.get("smtp_port") or "587"),
        "smtp_user": _env("BCI_IOT_SMTP_USER") or str(file_cfg.get("smtp_user") or ""),
        "smtp_password": _env("BCI_IOT_SMTP_PASSWORD")
        or str(file_cfg.get("smtp_password") or ""),
        "smtp_from": smtp_from or brand_from,
    }


def messaging_status() -> dict[str, Any]:
    cfg = _merged_settings()
    has_resend = bool(cfg.get("resend_api_key"))
    has_smtp = bool(cfg.get("smtp_host") and (cfg.get("smtp_from") or cfg.get("smtp_user")))
    return {
        "email_ready": has_resend or has_smtp,
        "sms_ready": False,
        "provider": "resend" if has_resend else ("smtp" if has_smtp else "none"),
        "brand_name": BRAND_NAME,
        "brand_from_email": cfg.get("brand_from_email") or DEFAULT_FROM_EMAIL,
        "resend_key_set": has_resend,
        "smtp_host": cfg.get("smtp_host") or "",
        "smtp_port": cfg.get("smtp_port") or "587",
        "smtp_user": cfg.get("smtp_user") or "",
        "smtp_from": cfg.get("smtp_from") or "",
        "smtp_password_set": bool(cfg.get("smtp_password")),
        "demo_allowed": _demo_allowed(),
    }


def _demo_allowed() -> bool:
    if _env("BCI_IOT_REQUIRE_REAL_OTP").lower() in {"1", "true", "yes", "on"}:
        return False
    flag = _env("BCI_IOT_OTP_DEMO").lower()
    if flag in {"0", "false", "no", "off"}:
        return False
    if flag in {"1", "true", "yes", "on"}:
        return True
    if _env("BCI_IOT_HTTPS").lower() in {"1", "true", "yes", "on"}:
        return False
    env = (_env("BCI_IOT_ENV") or "dev").lower()
    return env not in {"prod", "production"}


def mask_destination(destination: str, *, channel: Channel) -> str:
    dest = (destination or "").strip()
    if channel == "email":
        if "@" not in dest:
            return "***"
        local, _, domain = dest.partition("@")
        shown = (local[:1] + "***") if len(local) <= 2 else (local[:2] + "***")
        return f"{shown}@{domain}"
    digits = "".join(ch for ch in dest if ch.isdigit())
    if len(digits) < 4:
        return "***"
    return f"+***{digits[-4:]}"


def _shell_html(*, title: str, intro: str, middle_html: str, footer_extra: str = "") -> str:
    return f"""\
<!DOCTYPE html>
<html lang="it">
<head><meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" /></head>
<body style="margin:0;background:#f5f5f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;color:#1d1d1f;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f5f5f7;padding:32px 16px;">
    <tr><td align="center">
      <table role="presentation" width="100%" style="max-width:520px;background:#ffffff;border-radius:18px;overflow:hidden;">
        <tr><td style="padding:28px 28px 8px;">
          <p style="margin:0;font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:#86868b;font-weight:600;">{BRAND_NAME}</p>
          <h1 style="margin:12px 0 0;font-size:24px;line-height:1.25;font-weight:700;">{title}</h1>
        </td></tr>
        <tr><td style="padding:8px 28px 24px;">
          <p style="margin:0 0 20px;font-size:15px;line-height:1.55;color:#1d1d1f;">{intro}</p>
          {middle_html}
          <p style="margin:24px 0 0;font-size:12px;line-height:1.5;color:#86868b;">{SUPPORT_LINE}{footer_extra}</p>
        </td></tr>
        <tr><td style="padding:16px 28px 24px;border-top:1px solid #e8e8ed;">
          <p style="margin:0;font-size:11px;color:#aeaeb2;line-height:1.45;">
            © {BRAND_NAME} · Tesi UNITO · Messaggio automatico relativo al tuo account.
            Se non hai richiesto questa operazione, puoi ignorare questa email in sicurezza.
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""


def build_code_email(*, code: str, purpose: str) -> tuple[str, str, str]:
    labels = {
        "verify_email": "verifica del tuo indirizzo email",
        "verify_phone": "verifica telefono",
        "recover": "reimpostazione della password",
    }
    label = labels.get(purpose, "il tuo account")
    subject = f"{BRAND_NAME}: il tuo codice di sicurezza"
    text = (
        f"{BRAND_NAME}\n\n"
        f"Hai richiesto {label}.\n\n"
        f"Il tuo codice di sicurezza è: {code}\n\n"
        f"Il codice scade tra 10 minuti. Non condividerlo con nessuno.\n"
        f"Iris Nous non ti chiederà mai questo codice al telefono o in chat.\n\n"
        f"Se non sei stata/o tu, ignora questa email: la password non verrà modificata.\n\n"
        f"— Team {BRAND_NAME}\n"
    )
    middle = f"""
      <p style="margin:0 0 8px;font-size:13px;color:#86868b;">Codice di sicurezza</p>
      <p style="margin:0 0 20px;font-size:32px;letter-spacing:.35em;font-weight:700;text-align:center;font-family:ui-monospace,Menlo,Consolas,monospace;">{code}</p>
      <p style="margin:0;font-size:14px;line-height:1.5;color:#424245;">
        Valido per <strong>10 minuti</strong>. Usalo solo sulla pagina ufficiale di {BRAND_NAME}.
      </p>
    """
    html = _shell_html(
        title="Conferma la tua richiesta",
        intro=f"Hai richiesto <strong>{label}</strong> sul tuo account {BRAND_NAME}. "
        f"Usa il codice qui sotto per continuare.",
        middle_html=middle,
    )
    return subject, text, html


def build_signup_confirm_email(
    *, confirm_url: str, username: str, code: str
) -> tuple[str, str, str]:
    subject = f"Conferma la tua iscrizione a {BRAND_NAME}"
    text = (
        f"{BRAND_NAME}\n\n"
        f"Ciao {username},\n\n"
        f"grazie per esserti iscritta/o a {BRAND_NAME}.\n\n"
        f"Il modo piu' semplice (anche da un altro telefono): "
        f"torna sul sito Iris e inserisci questo codice:\n\n"
        f"  {code}\n\n"
        f"Oppure apri questo link sullo stesso dispositivo dove usi Iris:\n"
        f"{confirm_url}\n\n"
        f"Il codice e il link scadono tra 24 ore.\n"
        f"Se non trovi la mail, controlla Spam/Posta indesiderata "
        f"e segnalala come Non e' spam.\n\n"
        f"Se non hai creato tu questo account, ignora questa email.\n\n"
        f"— Team {BRAND_NAME}\n"
    )
    middle = f"""
      <p style="margin:0 0 8px;font-size:13px;color:#86868b;">Codice di conferma (consigliato)</p>
      <p style="margin:0 0 8px;font-size:32px;letter-spacing:.35em;font-weight:700;text-align:center;font-family:ui-monospace,Menlo,Consolas,monospace;">{code}</p>
      <p style="margin:0 0 22px;font-size:14px;line-height:1.5;color:#424245;">
        Scrivilo nella pagina <strong>Conferma la tua email</strong> sul dispositivo
        dove hai aperto Iris (funziona anche se leggi la mail da un altro telefono).
      </p>
      <p style="margin:0 0 12px;font-size:13px;color:#86868b;">Oppure, sullo stesso dispositivo / stessa rete del sito:</p>
      <table role="presentation" cellspacing="0" cellpadding="0" style="margin:0 0 20px;">
        <tr><td style="border-radius:980px;background:#1d1d1f;">
          <a href="{confirm_url}"
             style="display:inline-block;padding:14px 28px;color:#ffffff;text-decoration:none;font-size:15px;font-weight:600;">
            Conferma iscrizione
          </a>
        </td></tr>
      </table>
      <p style="margin:0;font-size:12px;line-height:1.5;color:#86868b;">
        Se il pulsante apre una pagina non trovata, ignoralo e usa solo il codice.
        Controlla anche Spam e segnala il messaggio come &quot;Non è spam&quot;.
      </p>
    """
    html = _shell_html(
        title="Conferma la tua iscrizione",
        intro=f"Ciao <strong>{username}</strong>, benvenuta/o in {BRAND_NAME}. "
        f"Per attivare l'account conferma il tuo indirizzo email.",
        middle_html=middle,
        footer_extra=" Codice e link scadono tra 24 ore.",
    )
    return subject, text, html


def build_support_reply_email(*, name: str, body: str) -> tuple[str, str, str]:
    who = (name or "").strip() or "ciao"
    safe_body = (
        (body or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br />")
    )
    subject = f"{BRAND_NAME}: risposta al tuo messaggio"
    text = (
        f"{BRAND_NAME}\n\n"
        f"Ciao {who},\n\n"
        f"ecco la risposta del team:\n\n"
        f"{body}\n\n"
        f"Se hai bisogno di altro, rispondi da Chatta con noi sul sito "
        f"oppure aspetta una nuova mail da questo indirizzo.\n\n"
        f"— Team {BRAND_NAME}\n"
    )
    middle = f"""
      <p style="margin:0;font-size:15px;line-height:1.6;color:#1d1d1f;">{safe_body}</p>
    """
    html = _shell_html(
        title="Risposta del team",
        intro=f"Ciao <strong>{who}</strong>, abbiamo letto il tuo messaggio.",
        middle_html=middle,
        footer_extra=" Questa mail è una risposta personale del team Iris Nous.",
    )
    return subject, text, html


def send_branded_email(
    *,
    destination: str,
    subject: str,
    text: str,
    html: str,
    demo_payload: str = "",
    demo_is_link: bool = False,
    demo_link: str = "",
) -> DeliveryResult:
    load_dotenv_file()
    errors: list[str] = []
    resend = _try_resend(destination, subject=subject, text=text, html=html)
    if resend is not None:
        if resend.ok:
            return resend
        errors.append(resend.detail)
    smtp = _try_smtp(destination, subject=subject, text=text, html=html)
    if smtp is not None:
        if smtp.ok:
            return smtp
        errors.append(smtp.detail)
    if _demo_allowed():
        link = demo_link or (demo_payload if demo_is_link else "")
        code = "" if demo_is_link else demo_payload
        return DeliveryResult(
            ok=True,
            channel="email",
            destination=destination,
            mode="demo",
            detail=(
                "Mail aziendale non ancora collegata: in locale trovi il contenuto qui sotto. "
                "Collega Gmail o Resend dalle impostazioni del server per l'invio reale."
            ),
            demo_code=code,
            demo_link=link,
        )
    return DeliveryResult(
        ok=False,
        channel="email",
        destination=destination,
        mode="demo",
        detail=(
            " ".join(errors).strip()
            or "Invio email non configurato. Collega Gmail SMTP oppure Resend "
            "nelle variabili del server."
        ),
        demo_code="" if demo_is_link else demo_payload,
        demo_link=demo_link or (demo_payload if demo_is_link else ""),
    )


def send_code(
    *,
    channel: Channel,
    destination: str,
    code: str,
    purpose: str,
) -> DeliveryResult:
    if channel != "email":
        return DeliveryResult(
            ok=False,
            channel=channel,
            destination=destination,
            mode="demo",
            detail="Per ora Iris manda i codici solo via email (niente SMS).",
        )
    subject, text, html = build_code_email(code=code, purpose=purpose)
    return send_branded_email(
        destination=destination,
        subject=subject,
        text=text,
        html=html,
        demo_payload=code,
        demo_is_link=False,
    )


def send_signup_confirmation(
    *, destination: str, username: str, confirm_url: str, code: str
) -> DeliveryResult:
    subject, text, html = build_signup_confirm_email(
        confirm_url=confirm_url, username=username, code=code
    )
    return send_branded_email(
        destination=destination,
        subject=subject,
        text=text,
        html=html,
        demo_payload=code,
        demo_is_link=False,
        demo_link=confirm_url,
    )


def build_pairing_email(
    *,
    name: str,
    code: str,
    pair_url: str,
    headset_id: str = "",
) -> tuple[str, str, str]:
    who = (name or "").strip() or "ciao"
    device = (headset_id or "").strip() or "la tua cuffia"
    subject = f"Il tuo codice Iris Nous: {code}"
    text = (
        f"{BRAND_NAME}\n\n"
        f"Ciao {who},\n\n"
        f"ecco il codice a 6 cifre per associare {device} e, se vuoi, lo smartphone.\n\n"
        f"  {code}\n\n"
        f"Apri la pagina di associazione (stesso account) e inserisci il codice:\n"
        f"{pair_url}\n\n"
        f"Non condividerlo. Se non hai chiesto tu questo codice, ignora la mail.\n\n"
        f"— Team {BRAND_NAME}\n"
    )
    middle = f"""
      <p style="margin:0 0 8px;font-size:13px;color:#86868b;">Codice di associazione</p>
      <p style="margin:0 0 18px;font-size:32px;letter-spacing:.35em;font-weight:700;text-align:center;font-family:ui-monospace,Menlo,Consolas,monospace;">{code}</p>
      <p style="margin:0 0 20px;font-size:14px;line-height:1.55;color:#424245;">
        Serve per collegare <strong>{device}</strong> e, se lo desideri, il ponte sullo smartphone.
        Aprilo sul dispositivo dove hai effettuato l’accesso.
      </p>
      <table role="presentation" cellspacing="0" cellpadding="0" style="margin:0 0 16px;">
        <tr><td style="border-radius:980px;background:#1d1d1f;">
          <a href="{pair_url}"
             style="display:inline-block;padding:14px 28px;color:#ffffff;text-decoration:none;font-size:15px;font-weight:600;">
            Apri associazione
          </a>
        </td></tr>
      </table>
      <p style="margin:0;font-size:12px;line-height:1.5;color:#86868b;">
        Se il pulsante non apre la pagina giusta, vai su Associa telefono nel menu e scrivi il codice a mano.
      </p>
    """
    html = _shell_html(
        title="Il tuo codice è pronto",
        intro=f"Ciao <strong>{who}</strong>, abbiamo generato il codice per il tuo ecosistema {BRAND_NAME}.",
        middle_html=middle,
    )
    return subject, text, html


def send_pairing_code(
    *,
    destination: str,
    code: str,
    name: str,
    pair_url: str,
    headset_id: str = "",
) -> DeliveryResult:
    subject, text, html = build_pairing_email(
        name=name, code=code, pair_url=pair_url, headset_id=headset_id
    )
    return send_branded_email(
        destination=destination,
        subject=subject,
        text=text,
        html=html,
        demo_payload=code,
        demo_is_link=False,
        demo_link=pair_url,
    )


def _from_header(cfg: dict[str, str]) -> str:
    addr = cfg.get("brand_from_email") or cfg.get("smtp_from") or DEFAULT_FROM_EMAIL
    return f"{BRAND_NAME} <{addr}>"


def _try_resend(
    to_addr: str, *, subject: str, text: str, html: str
) -> DeliveryResult | None:
    cfg = _merged_settings()
    api_key = cfg.get("resend_api_key") or ""
    if not api_key:
        return None
    payload = json.dumps(
        {
            "from": _from_header(cfg),
            "to": [to_addr],
            "subject": subject,
            "text": text,
            "html": html,
        }
    ).encode("utf-8")
    req = request.Request(
        "https://api.resend.com/emails",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with request.urlopen(req, timeout=20) as resp:
            if resp.status >= 400:
                raw = resp.read().decode("utf-8", errors="replace")
                return DeliveryResult(
                    ok=False,
                    channel="email",
                    destination=to_addr,
                    mode="resend",
                    detail=f"Invio Resend non riuscito (HTTP {resp.status}): {raw[:200]}",
                )
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
        return DeliveryResult(
            ok=False,
            channel="email",
            destination=to_addr,
            mode="resend",
            detail=f"Invio Resend non riuscito: {raw[:240]}",
        )
    except error.URLError as exc:
        return DeliveryResult(
            ok=False,
            channel="email",
            destination=to_addr,
            mode="resend",
            detail=f"Invio Resend non riuscito: {exc}",
        )
    return DeliveryResult(
        ok=True,
        channel="email",
        destination=to_addr,
        mode="resend",
        detail="Email inviata da Iris Nous.",
    )


def _try_smtp(
    to_addr: str, *, subject: str, text: str, html: str
) -> DeliveryResult | None:
    cfg = _merged_settings()
    host = cfg["smtp_host"]
    from_addr = cfg["smtp_from"] or cfg["brand_from_email"]
    if not host or not from_addr:
        return None
    user = cfg["smtp_user"]
    password = cfg["smtp_password"]
    port = int(cfg["smtp_port"] or "587")
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((BRAND_NAME, from_addr))
    msg["To"] = to_addr
    msg["Reply-To"] = from_addr
    msg["X-Mailer"] = f"{BRAND_NAME}"
    msg["List-Unsubscribe"] = f"<mailto:{from_addr}?subject=unsubscribe>"
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    try:
        context = ssl.create_default_context()
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=25, context=context) as smtp:
                if user and password:
                    smtp.login(user, password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=25) as smtp:
                smtp.ehlo()
                smtp.starttls(context=context)
                smtp.ehlo()
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
        detail="Email inviata da Iris Nous.",
    )
