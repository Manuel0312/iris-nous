"""Multi-device product site: showcase, login/register, access logs.

Run::

    uvicorn bci_iot.web.app:app --reload --host 0.0.0.0 --port 8000

"""

from __future__ import annotations

import os

import secrets

from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from fastapi.staticfiles import StaticFiles

from fastapi.templating import Jinja2Templates

from pydantic import BaseModel, Field

from starlette.middleware.sessions import SessionMiddleware

from bci_iot import __version__

from bci_iot.accounts.access_db import AccessDatabase

from bci_iot.accounts.gender import hello_line, welcome_back, welcome_new

from bci_iot.accounts.security import password_strength, secrets_equal

from bci_iot.accounts.timefmt import format_access_it

from bci_iot.accounts.store import ProfileStore, UserProfile
from bci_iot.accounts.phone_countries import PHONE_COUNTRIES
from bci_iot.accounts.validators import normalize_email
from bci_iot.accounts.messaging import (
    configure_messaging_store,
    load_dotenv_file,
    mask_destination,
    messaging_status,
    send_branded_email,
    send_code,
    send_signup_confirmation,
    send_pairing_code,
    update_messaging_config,
    build_support_reply_email,
)
from bci_iot.web.flags import ensure_flag_svgs, render_flag_svg
from bci_iot.web.i18n import (
    COOKIE_NAME,
    LANGUAGES,
    detect_language,
    get_request_language,
    make_translator,
    normalize_lang,
    set_request_language,
    translate,
)

DEFAULT_PUBLIC_URL = "https://iris-nous.onrender.com"

WEB_DIR = Path(__file__).resolve().parent

_STATIC_CACHE = "public, max-age=86400"


class CachedStaticFiles(StaticFiles):
    """Serve CSS/JS/immagini con Cache-Control, così un F5 non li riscarica."""

    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if getattr(response, "status_code", 500) < 400:
            response.headers["Cache-Control"] = _STATIC_CACHE
        return response

TEMPLATES = Jinja2Templates(directory=str(WEB_DIR / "templates"))
TEMPLATES.env.filters["it_time"] = format_access_it

class RegisterRequest(BaseModel):

    username: str = Field(min_length=1, max_length=64)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    headset_id: str = Field(default="", max_length=128)
    notes: str = ""
    action_map: dict[str, str] = Field(default_factory=dict)

class LoginRequest(BaseModel):

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)

class ProfileResponse(BaseModel):

    user_id: str
    username: str
    headset_id: str
    notes: str
    action_map: dict[str, str]
    is_admin: bool = False
    first_name: str = ""
    last_name: str = ""
    gender: str = ""
    email: str = ""
    phone_label: str = ""
    phone_display: str = ""
    email_verified: bool = False
    phone_verified: bool = False
    anagrafica_complete: bool = False
    @classmethod
    def from_profile(cls, profile: UserProfile) -> ProfileResponse:
        return cls(
            user_id=profile.user_id,
            username=profile.username,
            headset_id=profile.headset_id,
            notes=profile.notes,
            action_map=profile.action_map,
            is_admin=bool(profile.is_admin),
            first_name=profile.first_name,
            last_name=profile.last_name,
            gender=profile.gender,
            email=profile.email,
            phone_label=profile.phone_label,
            phone_display=profile.phone_display,
            email_verified=bool(profile.email_verified),
            phone_verified=bool(profile.phone_verified),
            anagrafica_complete=bool(profile.anagrafica_complete),
        )

class ConfigUpdateRequest(BaseModel):

    headset_id: str = Field(min_length=1, max_length=128)
    notes: str = ""
    action_map: dict[str, str] = Field(default_factory=dict)

class ImpulseRequest(BaseModel):

    command: str = Field(min_length=1, max_length=32)

class EventRequest(BaseModel):

    event: str = Field(min_length=1, max_length=32)

class CaptureRequest(BaseModel):
    command: str = Field(min_length=1, max_length=32)

def _session_username(request: Request) -> str | None:

    value = request.session.get("username")
    return str(value) if value else None

def _require_username(request: Request) -> str:

    username = _session_username(request)
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login required")
    return username

def _client_meta(request: Request) -> tuple[str, str]:

    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else ""
    ua = request.headers.get("user-agent", "")
    return ip, ua

def _flash(request: Request, message: str, kind: str = "ok") -> None:

    request.session["flash"] = {"message": message, "kind": kind}

def _pop_flash(request: Request) -> dict[str, str] | None:

    flash = request.session.pop("flash", None)
    return flash if isinstance(flash, dict) else None


def _configured_public_url() -> str:
    return (os.getenv("BCI_IOT_PUBLIC_URL") or DEFAULT_PUBLIC_URL).strip().rstrip("/")


def _host_is_local(request: Request) -> bool:
    host = (request.url.hostname or "").lower()
    if host in {"127.0.0.1", "localhost", "0.0.0.0", "::1"}:
        return True
    if host.startswith("192.168.") or host.startswith("10."):
        return True
    parts = host.split(".")
    if len(parts) >= 2 and parts[0] == "172" and parts[1].isdigit():
        return 16 <= int(parts[1]) <= 31
    return False


def create_app(

    data_dir: Path | str | None = None,
    *,
    session_secret: str | None = None,
    db_path: Path | str | None = None,
    admin_username: str | None = None,
    admin_password: str | None = None,

) -> FastAPI:

    """Application factory used by uvicorn and tests."""
    load_dotenv_file()
    try:
        ensure_flag_svgs(WEB_DIR / "static")
    except OSError:
        pass
    root = Path(__file__).resolve().parents[3]
    env_data = os.getenv("BCI_IOT_DATA_DIR", "").strip()
    if data_dir is not None:
        data_root = Path(data_dir)
    elif env_data:
        data_root = Path(env_data)
    else:
        data_root = root / "data"
    # Back-compat: tests pass a profiles folder; put DB beside it.
    if data_dir is not None and Path(data_dir).name == "profiles":
        profiles_dir = Path(data_dir)
        sqlite_path = Path(db_path) if db_path else profiles_dir.parent / "accessi.db"
        messaging_root = profiles_dir.parent
    elif data_dir is not None or env_data:
        base = Path(data_dir) if data_dir is not None else data_root
        profiles_dir = base / "profiles"
        sqlite_path = Path(db_path) if db_path else base / "accessi.db"
        messaging_root = base
    else:
        profiles_dir = data_root / "profiles"
        sqlite_path = Path(db_path) if db_path else data_root / "accessi.db"
        messaging_root = data_root
    configure_messaging_store(messaging_root)
    access_db = AccessDatabase(sqlite_path)
    store = ProfileStore(profiles_dir, access_db=access_db)
    secret = session_secret or os.getenv("BCI_IOT_SESSION_SECRET") or secrets.token_hex(32)
    admin_user = (admin_username or os.getenv("BCI_IOT_ADMIN_USERNAME") or "admin").strip() or "admin"
    if admin_password is not None:
        admin_pass = admin_password.strip() or "admin123"
    else:
        admin_pass = (os.getenv("BCI_IOT_ADMIN_PASSWORD") or "admin123").strip() or "admin123"
        # Online Render often keeps an old generated secret. The thesis admin
        # login is always this default, as requested by the project owner.
        admin_pass = "admin123"
    try:
        store.ensure_admin(admin_user, admin_pass)
    except ValueError:
        store.ensure_admin(admin_user, "admin123")
        admin_pass = "admin123"
    admin_profile = store.get(admin_user)
    if admin_profile is not None:
        access_db.upsert_anagrafica(
            username=admin_profile.username,
            user_id=admin_profile.user_id,
            first_name=admin_profile.first_name or "Admin",
            last_name=admin_profile.last_name or "",
            gender=admin_profile.gender or "non_binary",
            headset_id=admin_profile.headset_id,
            status="active",
            photo_path=admin_profile.photo_filename,
            email=admin_profile.email,
            phone_e164=admin_profile.phone_e164,
        )
    app = FastAPI(
        title="Iris",
        description="Product showcase, accounts, and local access logs.",
        version=__version__,
    )
    https_only = (os.getenv("BCI_IOT_HTTPS", "").strip().lower() in {"1", "true", "yes"})
    app.add_middleware(
        SessionMiddleware,
        secret_key=secret,
        session_cookie="bci_iot_session",
        same_site="lax",
        https_only=https_only,
        max_age=60 * 60 * 24 * 14,
        path="/",
    )

    @app.middleware("http")
    async def language_middleware(request: Request, call_next):
        request.state.lang = detect_language(request)
        return await call_next(request)

    app.mount("/static", CachedStaticFiles(directory=str(WEB_DIR / "static")), name="static")
    photos_dir = store.photos_dir
    photos_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/media/photos", CachedStaticFiles(directory=str(photos_dir)), name="photos")
    app.state.store = store
    app.state.access_db = access_db
    app.state.admin_username = admin_user
    app.state.photos_dir = photos_dir
    app.state.phone_queues: dict[str, list] = {}
    app.state.calib_sessions = {}
    def _store() -> ProfileStore:
        return store
    def _access() -> AccessDatabase:
        return access_db
    def _template_ctx(request: Request, profiles: ProfileStore, **extra: object) -> dict:
        username = _session_username(request)
        is_admin = False
        if username:
            profile = profiles.get(username)
            is_admin = bool(profile and profile.is_admin)
        lang = get_request_language(request)
        t = make_translator(lang)
        flash = _pop_flash(request)
        if flash and flash.get("message"):
            flash = {**flash, "message": translate(lang, str(flash["message"]))}
        cloud_url = _configured_public_url()
        site_is_local = _host_is_local(request)
        support_unread = 0
        if is_admin:
            support_unread = access_db.support_unread_count()
        return {
            "username": username,
            "is_admin": is_admin,
            "flash": flash,
            "phone_countries": PHONE_COUNTRIES,
            "lang": lang,
            "languages": LANGUAGES,
            "t": t,
            "cloud_url": cloud_url,
            "site_is_local": site_is_local,
            "admin_username": admin_user,
            "support_unread": support_unread,
            **extra,
        }

    def _redirect_with_lang(request: Request, url: str, lang: str) -> RedirectResponse:
        response = RedirectResponse(url, status_code=303)
        secure = https_only or str(request.url.scheme).lower() == "https"
        response.set_cookie(
            COOKIE_NAME,
            lang,
            max_age=60 * 60 * 24 * 365,
            httponly=False,
            samesite="lax",
            secure=secure,
            path="/",
        )
        return response
    def _public_base_url(request: Request) -> str:
        if _host_is_local(request):
            return str(request.base_url).rstrip("/")
        configured = (os.getenv("BCI_IOT_PUBLIC_URL") or "").strip().rstrip("/")
        if configured:
            return configured
        return str(request.base_url).rstrip("/")

    def _post_auth_destination(profile: UserProfile) -> str:
        if profile.is_admin:
            return "/accessi"
        if not profile.email_verified:
            return "/attendi-conferma-email"
        if profile.needs_anagrafica:
            return "/anagrafica"
        if profile.needs_calibration:
            return "/inizia"
        return "/dashboard"

    def _send_signup_mail(request: Request, profile: UserProfile):
        profile, raw, code = store.issue_signup_confirmation(profile.username)
        confirm_url = f"{_public_base_url(request)}/conferma-iscrizione/{raw}"
        delivery = send_signup_confirmation(
            destination=profile.email,
            username=profile.username,
            confirm_url=confirm_url,
            code=code,
        )
        sent_real = bool(delivery.ok and delivery.mode != "demo")
        if sent_real:
            request.session.pop("email_preview_code", None)
        else:
            request.session["email_preview_code"] = code
        return delivery

    def _pairing_mail_already_sent(profile: UserProfile) -> bool:
        last = str((profile.usage_stats or {}).get("pairing_emailed_code") or "")
        return bool(profile.pairing_code) and last == profile.pairing_code

    def _mark_pairing_mail_sent(profiles: ProfileStore, profile: UserProfile) -> UserProfile:
        stats = dict(profile.usage_stats or {})
        stats["pairing_emailed_code"] = profile.pairing_code
        profile.usage_stats = stats
        profiles.save(profile)
        return profile

    def _send_pairing_mail(
        request: Request,
        profiles: ProfileStore,
        profile: UserProfile,
        *,
        force: bool = False,
        flash: bool = False,
    ):
        profile = profiles.ensure_headset_pairing(profile.username)
        dest = (profile.email or "").strip()
        if not dest:
            if flash:
                _flash(
                    request,
                    "Aggiungi un’email al profilo per ricevere il codice di associazione.",
                    kind="error",
                )
            return profile, None
        if not force and _pairing_mail_already_sent(profile):
            return profile, None
        pair_url = f"{_public_base_url(request)}/associa-telefono"
        delivery = send_pairing_code(
            destination=dest,
            code=profile.pairing_code,
            name=profile.first_name or profile.username,
            pair_url=pair_url,
            headset_id=profile.headset_id,
        )
        if delivery.ok:
            profile = _mark_pairing_mail_sent(profiles, profile)
            if flash:
                if delivery.mode == "demo" and delivery.demo_code:
                    _flash(
                        request,
                        f"Codice inviato (demo locale): {delivery.demo_code}. "
                        "In produzione arriva via email.",
                        kind="ok",
                    )
                else:
                    masked = mask_destination(dest, channel="email")
                    _flash(
                        request,
                        f"Codice di associazione inviato via email a {masked}.",
                        kind="ok",
                    )
        elif flash:
            _flash(request, delivery.detail, kind="error")
        return profile, delivery

    def _continue(
        request: Request,
        *,
        next_url: str,
        message: str = "Accesso riuscito, un momento...",
    ) -> HTMLResponse:
        """Return 200 + client redirect.
        Some mobile browsers (Safari) drop Set-Cookie on 302/303 redirects after
        POST login, so the session never sticks on the phone.
        """
        response = TEMPLATES.TemplateResponse(
            request,
            "continue.html",
            {
                "next_url": next_url,
                "message": translate(get_request_language(request), message),
                "username": None,
                "is_admin": False,
                "flash": None,
                "lang": get_request_language(request),
                "languages": LANGUAGES,
                "t": make_translator(get_request_language(request)),
            },
        )
        response.headers["Cache-Control"] = "no-store"
        return response
    def _require_profile(
        request: Request,
        profiles: ProfileStore,
    ) -> UserProfile | RedirectResponse:
        username = _session_username(request)
        if not username:
            return RedirectResponse("/login", status_code=303)
        profile = profiles.get(username)
        if profile is None:
            request.session.clear()
            return RedirectResponse("/login", status_code=303)
        if not profile.is_admin and not profile.email_verified:
            return RedirectResponse("/attendi-conferma-email", status_code=303)
        profiles.touch_last_seen(username)
        return profiles.get(username) or profile
    def _log_access(
        request: Request,
        *,
        username: str,
        event: str,
        access: AccessDatabase,
    ) -> None:
        ip, ua = _client_meta(request)
        access.log(username=username, event=event, ip=ip, user_agent=ua)
    def _sync_anagrafica_db(profile: UserProfile, access: AccessDatabase) -> None:
        if not profile.anagrafica_complete:
            return
        access.upsert_anagrafica(
            username=profile.username,
            user_id=profile.user_id,
            first_name=profile.first_name,
            last_name=profile.last_name,
            gender=profile.gender,
            phone_label=profile.phone_label or profile.phone_display,
            headset_id=profile.headset_id,
            status="deleted" if profile.deleted_at else "active",
            photo_path=profile.photo_filename,
            email=profile.email,
            phone_e164=profile.phone_e164,
        )
    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/flags/{code}.svg")
    def serve_flag(code: str) -> Response:
        """Always-on SVG flags (no CDN, no writable static dir required)."""
        svg = render_flag_svg(code)
        return Response(
            content=svg,
            media_type="image/svg+xml; charset=utf-8",
            headers={"Cache-Control": "public, max-age=86400"},
        )

    @app.post("/lingua")
    async def set_language(request: Request) -> RedirectResponse:
        form = await request.form()
        lang = str(form.get("lang") or "")
        next_url = str(form.get("next") or form.get("next_url") or "/")
        code = set_request_language(request, lang)
        dest = next_url if next_url.startswith("/") and not next_url.startswith("//") else "/"
        return _redirect_with_lang(request, dest, code)

    @app.get("/lingua/{lang}")
    def set_language_get(request: Request, lang: str) -> RedirectResponse:
        code = set_request_language(request, lang)
        referer = request.headers.get("referer") or "/"
        dest = "/"
        if referer:
            try:
                from urllib.parse import urlparse

                path = urlparse(referer).path or "/"
                query = urlparse(referer).query
                if path.startswith("/lingua"):
                    dest = "/"
                elif path.startswith("/"):
                    dest = f"{path}?{query}" if query else path
            except Exception:
                dest = "/"
        return _redirect_with_lang(request, dest, code)

    @app.get("/", response_class=HTMLResponse)
    def home(
        request: Request,
        profiles: ProfileStore = Depends(_store),
    ) -> HTMLResponse:
        return TEMPLATES.TemplateResponse(
            request,
            "home.html",
            _template_ctx(request, profiles),
        )
    @app.get("/register", response_class=HTMLResponse)
    def register_page(
        request: Request,
        profiles: ProfileStore = Depends(_store),
    ) -> HTMLResponse:
        username = _session_username(request)
        if username:
            profile = profiles.get(username)
            if profile is not None:
                return RedirectResponse(_post_auth_destination(profile), status_code=303)
            return RedirectResponse("/dashboard", status_code=303)
        return TEMPLATES.TemplateResponse(
            request,
            "register.html",
            _template_ctx(request, profiles),
        )
    @app.post("/register")
    def register_submit(
        request: Request,
        username: str = Form(...),
        email: str = Form(...),
        password: str = Form(...),
        headset_id: str = Form(""),
        profiles: ProfileStore = Depends(_store),
        access: AccessDatabase = Depends(_access),
    ) -> HTMLResponse:
        try:
            profiles.create_account(username, password, email=email, headset_id=headset_id)
        except ValueError as exc:
            msg = str(exc)
            if _host_is_local(request):
                msg = (
                    f"{msg} "
                    "Se questo account è sul telefono, non registrarlo di nuovo qui: "
                    f"usa il sito online ({_configured_public_url()})."
                )
            _flash(request, msg, kind="error")
            return _continue(
                request,
                next_url="/register",
                message="Registrazione non riuscita, riprova...",
            )
        # Sync stub anagrafica row so admin list sees the username early
        created = profiles.get(username.strip())
        if created is not None:
            access.upsert_anagrafica(
                username=created.username,
                user_id=created.user_id,
                first_name="",
                last_name="",
                gender="",
                email=created.email,
            )
            delivery = _send_signup_mail(request, created)
            request.session["username"] = created.username
            _log_access(request, username=created.username, event="register", access=access)
            if not delivery.ok:
                _flash(
                    request,
                    "Account creato. La mail non è partita: usa il codice in questa pagina "
                    "e controlla anche Spam dopo aver premuto Reinvia.",
                    kind="error",
                )
            elif delivery.mode == "demo" and (delivery.demo_code or delivery.demo_link):
                bits = []
                if delivery.demo_code:
                    bits.append(f"codice {delivery.demo_code}")
                if delivery.demo_link:
                    bits.append(f"link {delivery.demo_link}")
                _flash(
                    request,
                    "Account creato (prova locale): " + " · ".join(bits),
                    kind="ok",
                )
            else:
                _flash(
                    request,
                    "Account creato. Controlla la posta (anche Spam): "
                    "c’è un codice da inserire qui, oppure il pulsante di conferma.",
                    kind="ok",
                )
        return _continue(
            request,
            next_url="/attendi-conferma-email",
            message="Controlla la tua email...",
        )

    @app.get("/attendi-conferma-email", response_class=HTMLResponse)
    def wait_email_confirm_page(
        request: Request,
        profiles: ProfileStore = Depends(_store),
    ) -> HTMLResponse:
        username = _session_username(request)
        if not username:
            return RedirectResponse("/login", status_code=303)
        profile = profiles.get(username)
        if profile is None:
            return RedirectResponse("/login", status_code=303)
        if profile.is_admin or profile.email_verified:
            request.session.pop("email_preview_code", None)
            return RedirectResponse(_post_auth_destination(profile), status_code=303)
        preview = str(request.session.get("email_preview_code") or "")
        return TEMPLATES.TemplateResponse(
            request,
            "attendi_conferma_email.html",
            _template_ctx(
                request,
                profiles,
                profile=profile,
                masked_email=mask_destination(profile.email, channel="email"),
                preview_code=preview,
            ),
        )

    @app.post("/attendi-conferma-email/reinvia")
    def resend_email_confirm(
        request: Request,
        profiles: ProfileStore = Depends(_store),
    ) -> RedirectResponse:
        username = _session_username(request)
        if not username:
            return RedirectResponse("/login", status_code=303)
        profile = profiles.get(username)
        if profile is None:
            return RedirectResponse("/login", status_code=303)
        if profile.email_verified:
            return RedirectResponse(_post_auth_destination(profile), status_code=303)
        try:
            delivery = _send_signup_mail(request, profile)
        except ValueError as exc:
            _flash(request, str(exc), kind="error")
            return RedirectResponse("/attendi-conferma-email", status_code=303)
        if not delivery.ok:
            _flash(
                request,
                "Non siamo riusciti a spedire la mail. Usa il codice in questa pagina "
                "e riprova tra un minuto.",
                kind="error",
            )
        elif delivery.mode == "demo" and (delivery.demo_code or delivery.demo_link):
            bits = []
            if delivery.demo_code:
                bits.append(f"codice {delivery.demo_code}")
            if delivery.demo_link:
                bits.append(f"link {delivery.demo_link}")
            _flash(request, "Nuova mail (locale): " + " · ".join(bits), kind="ok")
        else:
            _flash(
                request,
                "Ti abbiamo reinviato l'email. Controlla anche Spam e usa il codice nella pagina.",
                kind="ok",
            )
        return RedirectResponse("/attendi-conferma-email", status_code=303)

    @app.post("/attendi-conferma-email")
    def confirm_email_with_code(
        request: Request,
        code: str = Form(""),
        profiles: ProfileStore = Depends(_store),
        access: AccessDatabase = Depends(_access),
    ) -> RedirectResponse:
        username = _session_username(request)
        if not username:
            return RedirectResponse("/login", status_code=303)
        profile = profiles.get(username)
        if profile is None:
            return RedirectResponse("/login", status_code=303)
        if profile.email_verified:
            return RedirectResponse(_post_auth_destination(profile), status_code=303)
        try:
            profile = profiles.consume_otp(
                username, code=code, purpose="confirm_signup"
            )
        except ValueError as exc:
            _flash(request, str(exc), kind="error")
            return RedirectResponse("/attendi-conferma-email", status_code=303)
        _log_access(request, username=profile.username, event="email_confirmed", access=access)
        request.session.pop("email_preview_code", None)
        _flash(request, "Email confermata. Benvenuta/o in Iris Nous: completa i tuoi dati.", kind="ok")
        return RedirectResponse("/anagrafica", status_code=303)

    @app.get("/conferma-iscrizione/{token}", response_class=HTMLResponse)
    def confirm_signup(
        request: Request,
        token: str,
        profiles: ProfileStore = Depends(_store),
        access: AccessDatabase = Depends(_access),
    ) -> RedirectResponse:
        try:
            profile = profiles.confirm_email_with_token(token)
        except ValueError as exc:
            _flash(request, str(exc), kind="error")
            return RedirectResponse("/attendi-conferma-email", status_code=303)
        request.session["username"] = profile.username
        request.session.pop("email_preview_code", None)
        _log_access(request, username=profile.username, event="email_confirmed", access=access)
        _flash(request, "Email confermata. Benvenuta/o in Iris Nous: completa i tuoi dati.", kind="ok")
        return RedirectResponse("/anagrafica", status_code=303)

    @app.get("/login", response_class=HTMLResponse)
    def login_page(
        request: Request,
        profiles: ProfileStore = Depends(_store),
    ) -> HTMLResponse:
        username = _session_username(request)
        if username:
            profile = profiles.get(username)
            if profile is not None:
                return RedirectResponse(_post_auth_destination(profile), status_code=303)
            return RedirectResponse("/dashboard", status_code=303)
        return TEMPLATES.TemplateResponse(
            request,
            "login.html",
            _template_ctx(request, profiles),
        )
    @app.post("/login")
    def login_submit(
        request: Request,
        username: str = Form(...),
        password: str = Form(...),
        profiles: ProfileStore = Depends(_store),
        access: AccessDatabase = Depends(_access),
    ) -> HTMLResponse:
        profile = profiles.authenticate(username, password)
        if profile is None and username.strip().lower() == admin_user.lower():
            if secrets_equal(password, admin_pass) or secrets_equal(password, "admin123"):
                profiles.ensure_admin(admin_user, password)
                profile = profiles.authenticate(admin_user, password)
        if profile is None:
            _log_access(request, username=username.strip(), event="login_fail", access=access)
            if profiles.find_by_identifier(username.strip()) is not None:
                _flash(
                    request,
                    "Password non corretta. Puoi recuperarla da «Password dimenticata?».",
                    kind="error",
                )
            else:
                if _host_is_local(request):
                    _flash(
                        request,
                        "Nessun account con questi dati su questo sito locale. "
                        "Se ti sei iscritta dal telefono, entra dal sito online "
                        f"({_configured_public_url()}).",
                        kind="error",
                    )
                else:
                    _flash(
                        request,
                        "Nessun account con questi dati. "
                        "Se ti sei iscritta sul PC locale, quello è un database diverso: "
                        "entra con l’account creato qui, oppure iscriviti di nuovo sul sito online.",
                        kind="error",
                    )
            return _continue(
                request,
                next_url="/login?errore=1",
                message="Accesso non riuscito, riprova...",
            )
        request.session["username"] = profile.username
        _log_access(request, username=profile.username, event="login_ok", access=access)
        if profile.anagrafica_complete:
            _flash(
                request,
                welcome_back(
                    first_name=profile.first_name,
                    username=profile.username,
                    gender=profile.gender,
                ),
                kind="ok",
            )
        else:
            _flash(request, "Completa i tuoi dati per continuare.", kind="ok")
        dest = _post_auth_destination(profile)
        return _continue(
            request,
            next_url=dest,
            message="Accesso riuscito, un momento...",
        )

    @app.get("/recupera-password", response_class=HTMLResponse)
    def recover_password_page(
        request: Request,
        profiles: ProfileStore = Depends(_store),
    ) -> HTMLResponse:
        username = _session_username(request)
        if username:
            profile = profiles.get(username)
            if profile is not None:
                return RedirectResponse(_post_auth_destination(profile), status_code=303)
        step = request.session.get("recover_step") or "identify"
        recover_user = request.session.get("recover_user") or ""
        return TEMPLATES.TemplateResponse(
            request,
            "recupera_password.html",
            _template_ctx(
                request,
                profiles,
                recover_step=step,
                recover_user=recover_user,
                recover_channel=request.session.get("recover_channel") or "",
            ),
        )

    @app.post("/recupera-password")
    def recover_password_submit(
        request: Request,
        profiles: ProfileStore = Depends(_store),
        access: AccessDatabase = Depends(_access),
        identifier: str = Form(""),
        channel: str = Form("email"),
        code: str = Form(""),
        new_password: str = Form(""),
        new_password2: str = Form(""),
        action: str = Form("identify"),
    ) -> RedirectResponse:
        if action == "identify":
            profile = profiles.find_by_identifier(identifier)
            if profile is None:
                _flash(
                    request,
                    "Account non trovato. Prova con username o email.",
                    kind="error",
                )
                return RedirectResponse("/recupera-password", status_code=303)
            if not profile.email:
                _flash(
                    request,
                    "Questo account non ha un'email: non possiamo mandare il codice.",
                    kind="error",
                )
                return RedirectResponse("/recupera-password", status_code=303)
            try:
                profile, otp = profiles.issue_otp(
                    profile.username, channel="email", purpose="recover"
                )
            except ValueError as exc:
                _flash(request, str(exc), kind="error")
                return RedirectResponse("/recupera-password", status_code=303)
            dest = profile.email
            delivery = send_code(
                channel="email",
                destination=dest,
                code=otp,
                purpose="recover",
            )
            if not delivery.ok:
                _flash(request, delivery.detail, kind="error")
                return RedirectResponse("/recupera-password", status_code=303)
            request.session["recover_step"] = "code"
            request.session["recover_user"] = profile.username
            request.session["recover_channel"] = "email"
            masked = mask_destination(dest, channel="email")
            if delivery.mode == "demo" and delivery.demo_code:
                msg = (
                    f"Codice per {masked}: {delivery.demo_code} "
                    "(6 caratteri, senza spazi). Copialo qui sotto."
                )
            else:
                msg = (
                    f"Ti abbiamo inviato un'email da Iris Nous a {masked}. "
                    "Controlla la posta (anche spam): codice di 6 caratteri, senza spazi."
                )
            _flash(request, msg, kind="ok")
            return RedirectResponse("/recupera-password", status_code=303)

        recover_user = str(request.session.get("recover_user") or "")
        if not recover_user:
            _flash(request, "Sessione di recupero scaduta. Ricomincia.", kind="error")
            return RedirectResponse("/recupera-password", status_code=303)
        if new_password != new_password2:
            _flash(request, "Le nuove password non coincidono.", kind="error")
            return RedirectResponse("/recupera-password", status_code=303)
        try:
            profiles.consume_otp(recover_user, code=code, purpose="recover")
            profile = profiles.set_password(recover_user, new_password)
        except ValueError as exc:
            _flash(request, str(exc), kind="error")
            return RedirectResponse("/recupera-password", status_code=303)
        request.session.pop("recover_step", None)
        request.session.pop("recover_user", None)
        request.session.pop("recover_channel", None)
        _log_access(request, username=profile.username, event="password_reset", access=access)
        _flash(request, "Password aggiornata. Ora puoi accedere.", kind="ok")
        return RedirectResponse("/login", status_code=303)

    @app.get("/anagrafica", response_class=HTMLResponse)
    def anagrafica_page(
        request: Request,
        profiles: ProfileStore = Depends(_store),
    ) -> HTMLResponse:
        loaded = _require_profile(request, profiles)
        if isinstance(loaded, RedirectResponse):
            return loaded
        profile = loaded
        if profile.anagrafica_complete and request.query_params.get("edit") != "1":
            return RedirectResponse(_post_auth_destination(profile), status_code=303)
        return TEMPLATES.TemplateResponse(
            request,
            "anagrafica.html",
            _template_ctx(request, profiles, profile=profile),
        )

    @app.post("/anagrafica")
    def anagrafica_submit(
        request: Request,
        first_name: str = Form(...),
        last_name: str = Form(""),
        gender: str = Form(...),
        email: str = Form(""),
        phone_country: str = Form(""),
        phone_national: str = Form(""),
        phone_label: str = Form(""),
        profiles: ProfileStore = Depends(_store),
        access: AccessDatabase = Depends(_access),
    ) -> HTMLResponse:
        loaded = _require_profile(request, profiles)
        if isinstance(loaded, RedirectResponse):
            return loaded
        try:
            profile = profiles.update_anagrafica(
                loaded.username,
                first_name=first_name,
                last_name=last_name,
                gender=gender,
                email=email,
                phone_country=phone_country,
                phone_national=phone_national,
                phone_label=phone_label,
            )
        except ValueError as exc:
            _flash(request, str(exc), kind="error")
            return RedirectResponse("/anagrafica", status_code=303)
        _sync_anagrafica_db(profile, access)
        profiles.ensure_headset_pairing(profile.username)
        profile = profiles.get(profile.username) or profile
        _flash(
            request,
            welcome_new(
                first_name=profile.first_name,
                username=profile.username,
                gender=profile.gender,
            ),
            kind="ok",
        )
        next_url = "/dashboard" if profile.calibration_complete else "/inizia"
        return _continue(
            request,
            next_url=next_url,
            message="Dati salvati...",
        )
    @app.post("/logout")
    def logout(
        request: Request,
        access: AccessDatabase = Depends(_access),
    ) -> RedirectResponse:
        username = _session_username(request) or ""
        if username:
            _log_access(request, username=username, event="logout", access=access)
        request.session.clear()
        return RedirectResponse("/", status_code=303)
    @app.get("/accessi", response_class=HTMLResponse)
    def accessi_page(
        request: Request,
        profiles: ProfileStore = Depends(_store),
        access: AccessDatabase = Depends(_access),
    ) -> HTMLResponse:
        username = _session_username(request)
        if not username:
            return RedirectResponse("/login", status_code=303)
        profile = profiles.get(username)
        if profile is None or not profile.is_admin:
            _flash(request, "Solo l’amministratore può vedere gli accessi.", kind="error")
            return RedirectResponse("/", status_code=303)
        q = request.query_params.get("q", "")
        date_from = request.query_params.get("from", "")
        date_to = request.query_params.get("to", "")
        sort = request.query_params.get("sort", "name_asc")
        status_f = request.query_params.get("status", "active")
        allowed_sort = {
            "name_asc",
            "name_desc",
            "accesses_asc",
            "accesses_desc",
            "last_asc",
            "last_desc",
        }
        if sort not in allowed_sort:
            sort = "name_asc"
        if status_f not in {"active", "deleted", "all"}:
            status_f = "active"
        people = access.list_people(
            q=q,
            date_from=date_from,
            date_to=date_to,
            status=status_f,
            sort=sort,  # type: ignore[arg-type]
        )
        db_stats = access.stats()
        stats = {
            **db_stats,
            "online": profiles.count_online(),
            "registered": profiles.count_registered(),
            "deleted_accounts": profiles.count_deleted(),
        }
        return TEMPLATES.TemplateResponse(
            request,
            "accessi.html",
            _template_ctx(
                request,
                profiles,
                people=people,
                stats=stats,
                filters={
                    "q": q,
                    "from": date_from,
                    "to": date_to,
                    "sort": sort,
                    "status": status_f,
                },
                db_path=str(access.db_path),
            ),
        )

    @app.get("/invio-codici", response_class=HTMLResponse)
    def messaging_settings_page(
        request: Request,
        profiles: ProfileStore = Depends(_store),
    ) -> HTMLResponse:
        username = _session_username(request)
        if not username:
            return RedirectResponse("/login", status_code=303)
        profile = profiles.get(username)
        if profile is None or not profile.is_admin:
            _flash(request, "Solo l'amministratore può configurare l'invio codici.", kind="error")
            return RedirectResponse("/", status_code=303)
        return TEMPLATES.TemplateResponse(
            request,
            "invio_codici.html",
            _template_ctx(request, profiles, messaging=messaging_status()),
        )

    @app.post("/invio-codici")
    def messaging_settings_save(
        request: Request,
        profiles: ProfileStore = Depends(_store),
        brand_from_email: str = Form(""),
        resend_api_key: str = Form(""),
        smtp_host: str = Form(""),
        smtp_port: str = Form("587"),
        smtp_user: str = Form(""),
        smtp_password: str = Form(""),
        smtp_from: str = Form(""),
    ) -> RedirectResponse:
        username = _session_username(request)
        if not username:
            return RedirectResponse("/login", status_code=303)
        profile = profiles.get(username)
        if profile is None or not profile.is_admin:
            _flash(request, "Solo l'amministratore può configurare la mail Iris Nous.", kind="error")
            return RedirectResponse("/", status_code=303)
        update_messaging_config(
            brand_from_email=brand_from_email or None,
            resend_api_key=resend_api_key or None,
            smtp_host=smtp_host or None,
            smtp_port=smtp_port or "587",
            smtp_user=smtp_user or None,
            smtp_password=smtp_password or None,
            smtp_from=smtp_from or brand_from_email or None,
        )
        status = messaging_status()
        if status["email_ready"]:
            _flash(
                request,
                "Invio email attivo: i codici di recupero partiranno via email reale.",
                kind="ok",
            )
        else:
            _flash(
                request,
                "Salvato, ma manca ancora Resend API key oppure Gmail SMTP.",
                kind="error",
            )
        return RedirectResponse("/invio-codici", status_code=303)

    @app.get("/accessi/utente/{target}", response_class=HTMLResponse)
    def accessi_user_page(
        request: Request,
        target: str,
        profiles: ProfileStore = Depends(_store),
        access: AccessDatabase = Depends(_access),
    ) -> HTMLResponse:
        username = _session_username(request)
        if not username:
            return RedirectResponse("/login", status_code=303)
        admin = profiles.get(username)
        if admin is None or not admin.is_admin:
            _flash(request, "Solo l’amministratore può vedere gli accessi.", kind="error")
            return RedirectResponse("/", status_code=303)
        ana = access.get_anagrafica(target)
        user_profile = profiles.get(target)
        events = access.list_user_events(target)
        return TEMPLATES.TemplateResponse(
            request,
            "accessi_user.html",
            _template_ctx(
                request,
                profiles,
                target=target,
                anagrafica=ana,
                user_profile=user_profile.public_dict() if user_profile else None,
                events=events,
                support_threads=[
                    {
                        **thread,
                        "messages": access.list_support_messages(int(thread["id"])),
                    }
                    for thread in access.list_user_support_threads(
                        username=target,
                        email=(ana or {}).get("email")
                        or (user_profile.email if user_profile else ""),
                    )
                ],
            ),
        )

    def _admin_or_redirect(
        request: Request, profiles: ProfileStore
    ) -> UserProfile | RedirectResponse:
        username = _session_username(request)
        if not username:
            return RedirectResponse("/login", status_code=303)
        admin = profiles.get(username)
        if admin is None or not admin.is_admin:
            _flash(request, "Solo l’amministratore può aprire questa pagina.", kind="error")
            return RedirectResponse("/", status_code=303)
        return admin

    @app.get("/notifiche", response_class=HTMLResponse)
    def notifiche_page(
        request: Request,
        profiles: ProfileStore = Depends(_store),
        access: AccessDatabase = Depends(_access),
    ) -> HTMLResponse:
        admin = _admin_or_redirect(request, profiles)
        if isinstance(admin, RedirectResponse):
            return admin
        archive = request.query_params.get("archivio", "") in {"1", "true", "si"}
        threads = access.list_support_threads(archive=archive)
        return TEMPLATES.TemplateResponse(
            request,
            "notifiche.html",
            _template_ctx(
                request,
                profiles,
                threads=threads,
                archive=archive,
            ),
        )

    @app.get("/notifiche/{thread_id}", response_class=HTMLResponse)
    def notifica_thread_page(
        request: Request,
        thread_id: int,
        profiles: ProfileStore = Depends(_store),
        access: AccessDatabase = Depends(_access),
    ) -> HTMLResponse:
        admin = _admin_or_redirect(request, profiles)
        if isinstance(admin, RedirectResponse):
            return admin
        thread = access.get_support_thread(thread_id)
        if thread is None:
            _flash(request, "Messaggio non trovato.", kind="error")
            return RedirectResponse("/notifiche", status_code=303)
        access.mark_support_viewed(thread_id)
        thread = access.get_support_thread(thread_id) or thread
        messages = access.list_support_messages(thread_id)
        user_profile = profiles.get(str(thread.get("username") or ""))
        return TEMPLATES.TemplateResponse(
            request,
            "notifica.html",
            _template_ctx(
                request,
                profiles,
                thread=thread,
                messages=messages,
                user_profile=user_profile.public_dict() if user_profile else None,
            ),
        )

    @app.post("/notifiche/{thread_id}/rispondi")
    def notifica_reply(
        request: Request,
        thread_id: int,
        profiles: ProfileStore = Depends(_store),
        access: AccessDatabase = Depends(_access),
        body: str = Form(""),
    ) -> RedirectResponse:
        admin = _admin_or_redirect(request, profiles)
        if isinstance(admin, RedirectResponse):
            return admin
        thread = access.get_support_thread(thread_id)
        if thread is None:
            _flash(request, "Messaggio non trovato.", kind="error")
            return RedirectResponse("/notifiche", status_code=303)
        text = (body or "").strip()
        if len(text) < 2:
            _flash(request, "Scrivi una risposta prima di inviare.", kind="error")
            return RedirectResponse(f"/notifiche/{thread_id}", status_code=303)
        updated = access.add_admin_support_reply(thread_id, text)
        destination = ""
        if updated:
            destination = str(updated.get("guest_email") or "").strip()
        if not destination and thread.get("username"):
            person = profiles.get(str(thread["username"]))
            if person is not None:
                destination = person.email
        if destination and "@" in destination:
            display = str((updated or thread).get("guest_name") or "")
            if not display and thread.get("username"):
                person = profiles.get(str(thread["username"]))
                if person is not None:
                    display = f"{person.first_name} {person.last_name}".strip() or person.username
            subject, mail_text, mail_html = build_support_reply_email(name=display, body=text)
            result = send_branded_email(
                destination=destination,
                subject=subject,
                text=mail_text,
                html=mail_html,
                demo_payload=text,
            )
            if result.ok and result.mode == "demo":
                _flash(
                    request,
                    "Risposta salvata. Mail non collegata: in locale la risposta resta nella chat di tutela.",
                    kind="ok",
                )
            elif result.ok:
                _flash(request, f"Risposta inviata via email a {mask_destination(destination, channel='email')}.", kind="ok")
            else:
                _flash(
                    request,
                    "Risposta salvata nella chat, ma l’invio email non è riuscito. Controlla la configurazione email del server.",
                    kind="error",
                )
        else:
            _flash(
                request,
                "Risposta salvata nella chat di tutela. Manca un’email a cui scrivere.",
                kind="ok",
            )
        return RedirectResponse(f"/notifiche/{thread_id}", status_code=303)

    @app.get("/chatta", response_class=HTMLResponse)
    def chatta_page(
        request: Request,
        profiles: ProfileStore = Depends(_store),
    ) -> HTMLResponse:
        username = _session_username(request)
        profile = profiles.get(username) if username else None
        if profile is not None and profile.is_admin:
            return RedirectResponse("/notifiche", status_code=303)
        channel = (request.query_params.get("canale") or "chat").strip().lower()
        if channel not in {"chat", "email"}:
            channel = "chat"
        return TEMPLATES.TemplateResponse(
            request,
            "chatta.html",
            _template_ctx(request, profiles, profile=profile, contact_channel=channel),
        )

    @app.post("/chatta")
    def chatta_send(
        request: Request,
        profiles: ProfileStore = Depends(_store),
        access: AccessDatabase = Depends(_access),
        channel: str = Form("chat"),
        name: str = Form(""),
        email: str = Form(""),
        phone: str = Form(""),
        subject: str = Form(""),
        body: str = Form(""),
    ) -> RedirectResponse:
        username = _session_username(request) or ""
        profile = profiles.get(username) if username else None
        if profile is not None and profile.is_admin:
            _flash(request, "L’amministratore risponde dalle Notifiche.", kind="error")
            return RedirectResponse("/notifiche", status_code=303)
        text = (body or "").strip()
        if len(text) < 8:
            _flash(request, "Scrivi un messaggio un po’ più lungo (almeno 8 caratteri).", kind="error")
            return RedirectResponse("/chatta", status_code=303)
        guest_email = (email or "").strip()
        guest_name = (name or "").strip()
        guest_phone = (phone or "").strip()
        if profile is not None:
            guest_email = guest_email or profile.email
            guest_name = guest_name or f"{profile.first_name} {profile.last_name}".strip() or profile.username
            guest_phone = guest_phone or profile.phone_e164 or profile.phone_label
            username = profile.username
        else:
            username = ""
            if len(guest_name) < 2:
                _flash(request, "Scrivi il tuo nome, così sappiamo chi ci ha scritto.", kind="error")
                return RedirectResponse("/chatta", status_code=303)
            try:
                guest_email = normalize_email(guest_email)
            except ValueError:
                _flash(request, "Inserisci un’email a cui possiamo risponderti.", kind="error")
                return RedirectResponse("/chatta", status_code=303)
        access.add_user_support_message(
            username=username,
            guest_name=guest_name,
            guest_email=guest_email,
            guest_phone=guest_phone,
            channel=channel,
            subject=subject,
            body=text,
        )
        _flash(
            request,
            "Messaggio inviato. Ti risponderemo via email il prima possibile.",
            kind="ok",
        )
        return RedirectResponse("/chatta", status_code=303)

    @app.get("/dashboard", response_class=HTMLResponse)
    def dashboard(
        request: Request,
        profiles: ProfileStore = Depends(_store),
    ) -> HTMLResponse:
        loaded = _require_profile(request, profiles)
        if isinstance(loaded, RedirectResponse):
            return loaded
        profile = loaded
        if profile.is_admin:
            return RedirectResponse("/accessi", status_code=303)
        if profile.needs_anagrafica:
            return RedirectResponse("/anagrafica", status_code=303)
        stats = dict(profile.usage_stats or {})
        return TEMPLATES.TemplateResponse(
            request,
            "dashboard.html",
            _template_ctx(
                request,
                profiles,
                profile=profile,
                usage=stats,
                hello=hello_line(
                    first_name=profile.first_name,
                    username=profile.username,
                    gender=profile.gender,
                ),
            ),
        )

    @app.get("/cambia-password", response_class=HTMLResponse)
    def change_password_page(
        request: Request,
        profiles: ProfileStore = Depends(_store),
    ) -> HTMLResponse:
        loaded = _require_profile(request, profiles)
        if isinstance(loaded, RedirectResponse):
            return loaded
        return TEMPLATES.TemplateResponse(
            request,
            "cambia_password.html",
            _template_ctx(request, profiles, profile=loaded),
        )

    @app.post("/cambia-password")
    def change_password_submit(
        request: Request,
        current_password: str = Form(...),
        new_password: str = Form(...),
        new_password2: str = Form(...),
        profiles: ProfileStore = Depends(_store),
    ) -> RedirectResponse:
        loaded = _require_profile(request, profiles)
        if isinstance(loaded, RedirectResponse):
            return loaded
        if new_password != new_password2:
            _flash(request, "Le nuove password non coincidono.", kind="error")
            return RedirectResponse("/cambia-password", status_code=303)
        try:
            profiles.change_password(
                loaded.username,
                current_password=current_password,
                new_password=new_password,
            )
        except ValueError as exc:
            _flash(request, str(exc), kind="error")
            return RedirectResponse("/cambia-password", status_code=303)
        _flash(request, "Password aggiornata.", kind="ok")
        return RedirectResponse(
            "/accessi" if loaded.is_admin else "/dashboard",
            status_code=303,
        )

    @app.post("/anagrafica/foto")
    async def upload_photo(
        request: Request,
        photo: UploadFile = File(...),
        profiles: ProfileStore = Depends(_store),
        access: AccessDatabase = Depends(_access),
    ) -> RedirectResponse:
        loaded = _require_profile(request, profiles)
        if isinstance(loaded, RedirectResponse):
            return loaded
        back = "/anagrafica?edit=1" if loaded.anagrafica_complete else "/anagrafica"
        content_type = (photo.content_type or "").lower()
        if content_type not in {"image/jpeg", "image/png", "image/webp"}:
            _flash(request, "Formato foto non supportato (usa JPG, PNG o WebP).", kind="error")
            return RedirectResponse(back, status_code=303)
        raw = await photo.read()
        if len(raw) > 2_500_000:
            _flash(request, "Foto troppo grande (max 2.5 MB).", kind="error")
            return RedirectResponse(back, status_code=303)
        ext = ".jpg" if "jpeg" in content_type else ".png" if "png" in content_type else ".webp"
        filename = f"{loaded.user_id}{ext}"
        dest = Path(app.state.photos_dir) / filename
        dest.write_bytes(raw)
        profiles.set_photo(loaded.username, filename)
        updated = profiles.get(loaded.username)
        if updated:
            _sync_anagrafica_db(updated, access)
        _flash(request, "Foto profilo aggiornata.", kind="ok")
        return RedirectResponse(back, status_code=303)

    @app.post("/verifica/invia")
    def verify_send(
        request: Request,
        channel: str = Form(...),
        profiles: ProfileStore = Depends(_store),
    ) -> RedirectResponse:
        loaded = _require_profile(request, profiles)
        if isinstance(loaded, RedirectResponse):
            return loaded
        if channel not in {"email", "phone"}:
            _flash(request, "Canale non valido.", kind="error")
            return RedirectResponse("/anagrafica?edit=1", status_code=303)
        purpose = "verify_email" if channel == "email" else "verify_phone"
        try:
            profile, otp = profiles.issue_otp(
                loaded.username,
                channel=channel,  # type: ignore[arg-type]
                purpose=purpose,  # type: ignore[arg-type]
            )
        except ValueError as exc:
            _flash(request, str(exc), kind="error")
            return RedirectResponse("/anagrafica?edit=1" if loaded.anagrafica_complete else "/anagrafica", status_code=303)
        dest = profile.email if channel == "email" else profile.phone_e164
        delivery = send_code(
            channel=channel,  # type: ignore[arg-type]
            destination=dest,
            code=otp,
            purpose=purpose,
        )
        back = "/anagrafica?edit=1" if loaded.anagrafica_complete else "/anagrafica"
        if not delivery.ok:
            _flash(request, delivery.detail, kind="error")
            return RedirectResponse(back, status_code=303)
        if delivery.mode == "demo" and delivery.demo_code:
            _flash(
                request,
                f"Demo locale: codice {delivery.demo_code} (6 caratteri, senza spazi).",
                kind="ok",
            )
        else:
            masked = mask_destination(dest, channel=channel)  # type: ignore[arg-type]
            where = "email" if channel == "email" else "SMS"
            _flash(
                request,
                f"Codice inviato via {where} a {masked}. Scade tra 10 minuti.",
                kind="ok",
            )
        return RedirectResponse(back, status_code=303)

    @app.post("/verifica/conferma")
    def verify_confirm(
        request: Request,
        channel: str = Form(...),
        code: str = Form(...),
        profiles: ProfileStore = Depends(_store),
        access: AccessDatabase = Depends(_access),
    ) -> RedirectResponse:
        loaded = _require_profile(request, profiles)
        if isinstance(loaded, RedirectResponse):
            return loaded
        purpose = "verify_email" if channel == "email" else "verify_phone"
        try:
            profile = profiles.consume_otp(
                loaded.username,
                code=code,
                purpose=purpose,  # type: ignore[arg-type]
            )
        except ValueError as exc:
            _flash(request, str(exc), kind="error")
            return RedirectResponse("/anagrafica?edit=1", status_code=303)
        _sync_anagrafica_db(profile, access)
        _flash(
            request,
            "Email verificata." if channel == "email" else "Telefono verificato.",
            kind="ok",
        )
        return RedirectResponse("/anagrafica?edit=1", status_code=303)

    @app.post("/elimina-account")
    def delete_account(
        request: Request,
        profiles: ProfileStore = Depends(_store),
        access: AccessDatabase = Depends(_access),
    ) -> RedirectResponse:
        loaded = _require_profile(request, profiles)
        if isinstance(loaded, RedirectResponse):
            return loaded
        try:
            profiles.soft_delete(loaded.username)
            access.mark_deleted(loaded.username)
        except ValueError as exc:
            _flash(request, str(exc), kind="error")
            return RedirectResponse("/anagrafica?edit=1", status_code=303)
        request.session.clear()
        _flash(request, "Account eliminato.", kind="ok")
        return RedirectResponse("/", status_code=303)

    @app.get("/api/password-strength")
    def api_password_strength(password: str = "") -> dict:
        check = password_strength(password)
        return {"ok": check.ok, "level": check.level, "message": check.message}

    # --- Calibrazione cuffia (parola ↔ segnale) + associazione telefono ---
    def _calib_session_for(username: str, profiles: ProfileStore):
        from bci_iot.pipeline.calibration_wizard import CalibrationSession

        profile = profiles.ensure_headset_pairing(username)
        sessions = app.state.calib_sessions
        sess = sessions.get(username)
        if sess is None or sess.headset_id != profile.headset_id:
            sess = CalibrationSession(
                username=username,
                headset_id=profile.headset_id,
                pairing_code=profile.pairing_code,
            )
            sessions[username] = sess
        return sess, profile

    @app.get("/inizia", response_class=HTMLResponse)
    def inizia_page(
        request: Request,
        profiles: ProfileStore = Depends(_store),
    ) -> HTMLResponse:
        loaded = _require_profile(request, profiles)
        if isinstance(loaded, RedirectResponse):
            return loaded
        profile = loaded
        if profile.is_admin:
            return RedirectResponse("/accessi", status_code=303)
        if profile.needs_anagrafica:
            return RedirectResponse("/anagrafica", status_code=303)
        return TEMPLATES.TemplateResponse(
            request,
            "inizia.html",
            _template_ctx(request, profiles, profile=profile),
        )

    @app.get("/calibrazione", response_class=HTMLResponse)
    def calibrazione_page(
        request: Request,
        profiles: ProfileStore = Depends(_store),
    ) -> HTMLResponse:
        loaded = _require_profile(request, profiles)
        if isinstance(loaded, RedirectResponse):
            return loaded
        profile = loaded
        if profile.needs_anagrafica:
            return RedirectResponse("/anagrafica", status_code=303)
        profiles.ensure_headset_pairing(profile.username)
        profile = profiles.get(profile.username) or profile
        done_flag = request.query_params.get("done") == "1"
        passo_raw = (request.query_params.get("passo") or "").strip()
        if done_flag:
            done = True
            passo = 0
        elif passo_raw:
            done = False
            try:
                passo = int(passo_raw)
            except ValueError:
                passo = 1
            passo = min(3, max(1, passo))
        elif profile.calibration_complete:
            done = True
            passo = 0
        else:
            done = False
            passo = 1
        acc_raw = request.query_params.get("acc")
        accuracy = None
        if acc_raw is not None:
            try:
                accuracy = float(acc_raw)
            except ValueError:
                accuracy = None
        from bci_iot.pipeline.calibration_wizard import (
            SAMPLES_PER_COLOUR,
            colour_targets_public,
        )

        return TEMPLATES.TemplateResponse(
            request,
            "calibrazione.html",
            _template_ctx(
                request,
                profiles,
                profile=profile,
                colours=colour_targets_public(),
                samples_needed=SAMPLES_PER_COLOUR,
                done=done,
                passo=passo,
                accuracy=accuracy,
                pairing_mail_sent=_pairing_mail_already_sent(profile),
                pairing_email_masked=mask_destination(profile.email or "", channel="email")
                if profile.email
                else "",
            ),
        )

    @app.post("/api/calibrate/capture")
    async def api_calibrate_capture(
        request: Request,
        payload: CaptureRequest,
        profiles: ProfileStore = Depends(_store),
    ) -> dict:
        username = _session_username(request)
        if not username:
            raise HTTPException(status_code=401, detail="Login required")
        sess, _profile = _calib_session_for(username, profiles)
        try:
            # EEG / prior synthesis may block (BrainFlow poll + sleep); keep event loop free.
            result = await run_in_threadpool(sess.capture, payload.command)
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "command": result.command,
            "intent": result.intent,
            "intensity": result.intensity,
            "alpha": result.alpha,
            "beta": result.beta,
            "samples_for_word": result.samples_for_word,
            "needed_for_word": result.needed_for_word,
            "progress": result.progress,
            "complete_enough": result.complete_enough,
            "folder": result.folder,
            "color_name": result.color_name,
            "cue": result.cue,
        }

    @app.post("/api/calibrate/finish")
    async def api_calibrate_finish(
        request: Request,
        profiles: ProfileStore = Depends(_store),
    ) -> dict:
        username = _session_username(request)
        if not username:
            raise HTTPException(status_code=401, detail="Login required")
        sess = app.state.calib_sessions.get(username)
        if sess is None:
            raise HTTPException(status_code=400, detail="Nessuna sessione di calibrazione")
        root = Path(__file__).resolve().parents[3]
        try:
            path, accuracy = await run_in_threadpool(
                sess.finish, models_dir=root / "models" / "users"
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        profiles.mark_calibration_complete(username)
        app.state.calib_sessions.pop(username, None)
        return {"status": "ok", "model_path": str(path), "accuracy": accuracy}

    @app.get("/associa-telefono", response_class=HTMLResponse)
    def associa_telefono_page(
        request: Request,
        profiles: ProfileStore = Depends(_store),
    ) -> HTMLResponse:
        from bci_iot.integrations.spotify_oauth import (
            pairing_qr_url,
            public_site_url,
            spotify_configured,
        )

        loaded = _require_profile(request, profiles)
        if isinstance(loaded, RedirectResponse):
            return loaded
        profile = profiles.ensure_headset_pairing(loaded.username)
        base = str(request.base_url)
        public = public_site_url(base)
        pair_link = f"{public}/associa-telefono"
        return TEMPLATES.TemplateResponse(
            request,
            "associa_telefono.html",
            _template_ctx(
                request,
                profiles,
                profile=profile,
                public_url=public,
                qr_url=pairing_qr_url(pair_link),
                spotify_ready=spotify_configured(),
            ),
        )

    @app.post("/associa-telefono")
    def associa_telefono_submit(
        request: Request,
        code: str = Form(...),
        profiles: ProfileStore = Depends(_store),
    ) -> HTMLResponse:
        loaded = _require_profile(request, profiles)
        if isinstance(loaded, RedirectResponse):
            return loaded
        try:
            profile = profiles.confirm_phone_pairing(loaded.username, code)
        except ValueError as exc:
            _flash(request, str(exc), kind="error")
            return RedirectResponse("/associa-telefono", status_code=303)
        _flash(request, "Telefono associato. Apri Telefono live e collega Spotify.", kind="ok")
        dest = "/telefono" if not profile.needs_calibration else "/calibrazione?passo=2"
        return _continue(
            request,
            next_url=dest,
            message="Associazione riuscita...",
        )

    @app.post("/associa-telefono/unpair")
    def associa_telefono_unpair(
        request: Request,
        profiles: ProfileStore = Depends(_store),
    ) -> RedirectResponse:
        loaded = _require_profile(request, profiles)
        if isinstance(loaded, RedirectResponse):
            return loaded
        profiles.unpair_phone(loaded.username)
        app.state.phone_queues.pop(loaded.username, None)
        _flash(request, "Telefono scollegato. Nuovo codice pronto: invialo via email quando vuoi.", kind="ok")
        return RedirectResponse("/associa-telefono", status_code=303)

    @app.post("/associa-telefono/invia-codice")
    def associa_telefono_send_code(
        request: Request,
        profiles: ProfileStore = Depends(_store),
    ) -> RedirectResponse:
        loaded = _require_profile(request, profiles)
        if isinstance(loaded, RedirectResponse):
            return loaded
        _send_pairing_mail(request, profiles, loaded, force=True, flash=True)
        back = request.headers.get("referer") or ""
        if "/calibrazione" in back:
            return RedirectResponse("/calibrazione?passo=1", status_code=303)
        return RedirectResponse("/associa-telefono", status_code=303)

    @app.get("/telefono", response_class=HTMLResponse)
    def telefono_live_page(
        request: Request,
        profiles: ProfileStore = Depends(_store),
    ) -> HTMLResponse:
        loaded = _require_profile(request, profiles)
        if isinstance(loaded, RedirectResponse):
            return loaded
        profile = profiles.ensure_headset_pairing(loaded.username)
        if profile.phone_paired:
            profiles.touch_phone(profile.username)
            profile = profiles.get(profile.username) or profile
        return TEMPLATES.TemplateResponse(
            request,
            "telefono.html",
            _template_ctx(request, profiles, profile=profile),
        )

    @app.post("/api/phone/heartbeat")
    def api_phone_heartbeat(
        request: Request,
        profiles: ProfileStore = Depends(_store),
    ) -> dict:
        username = _session_username(request)
        if not username:
            raise HTTPException(status_code=401, detail="Login required")
        profile = profiles.get(username)
        if profile is None:
            raise HTTPException(status_code=404, detail="Profile not found")
        if not profile.phone_paired:
            return {"status": "error", "detail": "Telefono non associato", "events": []}
        profiles.touch_phone(username)
        events = list(app.state.phone_queues.get(username) or [])
        return {"status": "ok", "events": events, "spotify_linked": profile.spotify_linked}

    @app.get("/auth/spotify/start")
    def spotify_start(
        request: Request,
        profiles: ProfileStore = Depends(_store),
    ) -> RedirectResponse:
        from bci_iot.integrations.spotify_oauth import (
            authorize_url,
            new_oauth_state,
            redirect_uri,
            spotify_configured,
        )

        loaded = _require_profile(request, profiles)
        if isinstance(loaded, RedirectResponse):
            return loaded
        if not spotify_configured():
            _flash(request, "Spotify non configurato sul server.", kind="error")
            return RedirectResponse("/associa-telefono", status_code=303)
        state = new_oauth_state()
        request.session["spotify_oauth_state"] = state
        redir = redirect_uri(str(request.base_url))
        return RedirectResponse(authorize_url(redirect=redir, state=state), status_code=302)

    @app.get("/auth/spotify/callback")
    def spotify_callback(
        request: Request,
        code: str = "",
        state: str = "",
        error: str = "",
        profiles: ProfileStore = Depends(_store),
    ) -> RedirectResponse:
        from bci_iot.integrations.spotify_oauth import (
            exchange_code,
            fetch_me,
            redirect_uri,
            token_expiry_iso,
        )

        loaded = _require_profile(request, profiles)
        if isinstance(loaded, RedirectResponse):
            return loaded
        if error:
            _flash(request, f"Spotify ha rifiutato: {error}", kind="error")
            return RedirectResponse("/associa-telefono", status_code=303)
        expected = request.session.pop("spotify_oauth_state", None)
        if not code or not state or state != expected:
            _flash(request, "Sessione Spotify non valida. Riprova.", kind="error")
            return RedirectResponse("/associa-telefono", status_code=303)
        redir = redirect_uri(str(request.base_url))
        try:
            tokens = exchange_code(code, redirect=redir)
            access = str(tokens.get("access_token") or "")
            refresh = str(tokens.get("refresh_token") or "")
            expires_at = token_expiry_iso(int(tokens.get("expires_in") or 3600))
            me = fetch_me(access) if access else {}
            profiles.set_spotify_tokens(
                loaded.username,
                access_token=access,
                refresh_token=refresh,
                expires_at=expires_at,
                user_id=str(me.get("id") or ""),
                display_name=str(me.get("display_name") or me.get("id") or ""),
            )
        except Exception as exc:  # noqa: BLE001
            _flash(request, f"Collegamento Spotify fallito: {exc}", kind="error")
            return RedirectResponse("/associa-telefono", status_code=303)
        _flash(request, "Spotify collegato. Apri Spotify sul telefono e prova il test.", kind="ok")
        return RedirectResponse("/associa-telefono", status_code=303)

    @app.post("/auth/spotify/disconnect")
    def spotify_disconnect(
        request: Request,
        profiles: ProfileStore = Depends(_store),
    ) -> RedirectResponse:
        loaded = _require_profile(request, profiles)
        if isinstance(loaded, RedirectResponse):
            return loaded
        profiles.clear_spotify(loaded.username)
        _flash(request, "Spotify scollegato.", kind="ok")
        return RedirectResponse("/associa-telefono", status_code=303)

    @app.post("/api/music/next")
    def api_music_next(
        request: Request,
        profiles: ProfileStore = Depends(_store),
    ) -> dict:
        from bci_iot.integrations.music_control import run_spotify_action

        username = _session_username(request)
        if not username:
            raise HTTPException(status_code=401, detail="Login required")
        profile = profiles.get(username)
        if profile is None:
            raise HTTPException(status_code=404, detail="Profile not found")
        queue = app.state.phone_queues.setdefault(username, [])
        return run_spotify_action(profiles, profile, "next_track", queue=queue)

    @app.post("/api/music/pause")
    def api_music_pause(
        request: Request,
        profiles: ProfileStore = Depends(_store),
    ) -> dict:
        from bci_iot.integrations.music_control import run_spotify_action

        username = _session_username(request)
        if not username:
            raise HTTPException(status_code=401, detail="Login required")
        profile = profiles.get(username)
        if profile is None:
            raise HTTPException(status_code=404, detail="Profile not found")
        queue = app.state.phone_queues.setdefault(username, [])
        return run_spotify_action(profiles, profile, "pause", queue=queue)

    @app.post("/dashboard")
    def dashboard_save(
        request: Request,
        headset_id: str = Form(...),
        notes: str = Form(""),
        action_focus: str = Form("spotify.next_track"),
        action_relax: str = Form("spotify.pause"),
        action_accept: str = Form("phone.accept_call"),
        action_reject: str = Form("phone.reject_call"),
        profiles: ProfileStore = Depends(_store),
        access: AccessDatabase = Depends(_access),
    ) -> RedirectResponse:
        username = _session_username(request)
        if not username:
            return RedirectResponse("/login", status_code=303)
        action_map = {
            "FOCUS": action_focus.strip(),
            "RELAX": action_relax.strip(),
            "ACCEPT": action_accept.strip(),
            "REJECT": action_reject.strip(),
        }
        try:
            profiles.update_config(
                username,
                headset_id=headset_id,
                notes=notes,
                action_map=action_map,
            )
        except KeyError:
            request.session.clear()
            return RedirectResponse("/login", status_code=303)
        profile = profiles.get(username)
        if profile is not None:
            _sync_anagrafica_db(profile, access)
        _flash(request, "Configurazione salvata.", kind="ok")
        return RedirectResponse("/dashboard", status_code=303)
    @app.post("/api/auth/register", response_model=ProfileResponse)
    def api_register(
        request: Request,
        body: RegisterRequest,
        profiles: ProfileStore = Depends(_store),
        access: AccessDatabase = Depends(_access),
    ) -> ProfileResponse:
        try:
            profile = profiles.create_account(
                body.username,
                body.password,
                email=body.email,
                headset_id=body.headset_id,
                notes=body.notes,
                action_map=body.action_map,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        request.session["username"] = profile.username
        _log_access(request, username=profile.username, event="register", access=access)
        return ProfileResponse.from_profile(profile)
    @app.post("/api/auth/login", response_model=ProfileResponse)
    def api_login(
        request: Request,
        body: LoginRequest,
        profiles: ProfileStore = Depends(_store),
        access: AccessDatabase = Depends(_access),
    ) -> ProfileResponse:
        profile = profiles.authenticate(body.username, body.password)
        if profile is None:
            _log_access(
                request,
                username=body.username.strip(),
                event="login_fail",
                access=access,
            )
            raise HTTPException(status_code=401, detail="Invalid credentials")
        request.session["username"] = profile.username
        _log_access(request, username=profile.username, event="login_ok", access=access)
        return ProfileResponse.from_profile(profile)
    @app.post("/api/auth/logout")
    def api_logout(
        request: Request,
        access: AccessDatabase = Depends(_access),
    ) -> dict[str, str]:
        username = _session_username(request) or ""
        if username:
            _log_access(request, username=username, event="logout", access=access)
        request.session.clear()
        return {"status": "ok"}
    @app.get("/api/me", response_model=ProfileResponse)
    def api_me(
        request: Request,
        profiles: ProfileStore = Depends(_store),
    ) -> ProfileResponse:
        username = _require_username(request)
        profile = profiles.get(username)
        if profile is None:
            raise HTTPException(status_code=404, detail="Profile not found")
        return ProfileResponse.from_profile(profile)
    @app.put("/api/me/config", response_model=ProfileResponse)
    def api_update_me(
        request: Request,
        body: ConfigUpdateRequest,
        profiles: ProfileStore = Depends(_store),
    ) -> ProfileResponse:
        username = _require_username(request)
        try:
            profile = profiles.update_config(
                username,
                headset_id=body.headset_id,
                notes=body.notes,
                action_map=body.action_map,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Profile not found") from exc
        return ProfileResponse.from_profile(profile)
    @app.get("/api/admin/accessi")
    def api_accessi(
        request: Request,
        profiles: ProfileStore = Depends(_store),
        access: AccessDatabase = Depends(_access),
    ) -> dict:
        username = _session_username(request)
        if not username:
            raise HTTPException(status_code=401, detail="Login required")
        profile = profiles.get(username)
        if profile is None or not profile.is_admin:
            raise HTTPException(status_code=403, detail="Admin only")
        return {
            "stats": {
                **access.stats(),
                "online": profiles.count_online(),
                "registered": profiles.count_registered(),
                "deleted_accounts": profiles.count_deleted(),
            },
            "people": [
                {
                    "username": p.username,
                    "first_name": p.first_name,
                    "last_name": p.last_name,
                    "access_count": p.access_count,
                    "first_access": p.first_access,
                    "last_access": p.last_access,
                    "status": p.status,
                }
                for p in access.list_people(status="all")
            ],
        }
    # --- Context demo (channels + Alexa short confirm) + legacy engines ---
    app.state.demo_engine = None
    app.state.dialogue_engine = None
    app.state.context_engine = None
    app.state.folder_engine = None
    def _demo_engine():
        if app.state.demo_engine is None:
            from bci_iot.pipeline.impulse_demo import ImpulseDemoEngine
            app.state.demo_engine = ImpulseDemoEngine(seed=11)
        return app.state.demo_engine
    def _dialogue_engine():
        if app.state.dialogue_engine is None:
            from bci_iot.pipeline.dialogue_demo import DialogueDemoEngine
            app.state.dialogue_engine = DialogueDemoEngine(seed=11)
        return app.state.dialogue_engine
    def _context_engine():
        if app.state.context_engine is None:
            from bci_iot.pipeline.context_demo import ContextDemoEngine
            app.state.context_engine = ContextDemoEngine(seed=11)
        return app.state.context_engine

    def _folder_engine():
        if app.state.folder_engine is None:
            from bci_iot.pipeline.macro_folders import MacroFolderEngine
            app.state.folder_engine = MacroFolderEngine()
        return app.state.folder_engine

    @app.get("/cartelle", response_class=HTMLResponse)
    def cartelle_page(
        request: Request,
        profiles: ProfileStore = Depends(_store),
    ) -> HTMLResponse:
        return TEMPLATES.TemplateResponse(
            request,
            "cartelle.html",
            _template_ctx(request, profiles),
        )

    @app.get("/api/folders/status")
    def folders_status() -> dict:
        return _folder_engine().status()

    @app.post("/api/folders")
    def folders_fire(body: ImpulseRequest) -> dict:
        try:
            return _folder_engine().fire(body.command)
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/demo", response_class=HTMLResponse)
    def demo_page(
        request: Request,
        profiles: ProfileStore = Depends(_store),
    ) -> HTMLResponse:
        from bci_iot.pipeline.context_demo import list_context_commands
        return TEMPLATES.TemplateResponse(
            request,
            "demo.html",
            _template_ctx(request, profiles, commands=list_context_commands()),
        )
    @app.get("/api/demo/context/status")
    def demo_context_status() -> dict:
        return _context_engine().status()
    @app.post("/api/demo/context")
    def demo_context_fire(body: ImpulseRequest) -> dict:
        try:
            return _context_engine().fire(body.command)
        except KeyError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown command: {body.command}",
            ) from exc
    @app.post("/api/demo/context/event")
    def demo_context_event(body: EventRequest) -> dict:
        engine = _context_engine()
        ev = body.event.strip().lower()
        if ev == "message":
            return engine.event_message()
        if ev == "call":
            return engine.event_call()
        if ev == "music_on":
            return engine.event_music(True)
        if ev == "music_off":
            return engine.event_music(False)
        if ev == "clear":
            return engine.event_clear()
        raise HTTPException(status_code=400, detail=f"Unknown event: {body.event}")
    @app.get("/api/demo/dialogue/status")
    def demo_dialogue_status() -> dict:
        return _dialogue_engine().status()
    @app.post("/api/demo/dialogue")
    def demo_dialogue(body: ImpulseRequest) -> dict:
        try:
            return _dialogue_engine().fire(body.command)
        except KeyError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown command: {body.command}. Use MENU, SI, NO.",
            ) from exc
    @app.post("/api/demo/impulse")
    def demo_impulse(body: ImpulseRequest) -> dict:
        try:
            return _demo_engine().fire(body.command)
        except KeyError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown command: {body.command}",
            ) from exc
    return app

app = create_app()
