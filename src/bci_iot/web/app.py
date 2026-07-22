"""Multi-device product site: showcase, login/register, access logs.

Run::

    uvicorn bci_iot.web.app:app --reload --host 0.0.0.0 --port 8000

"""

from __future__ import annotations

import os

import secrets

from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, status

from fastapi.responses import HTMLResponse, RedirectResponse

from fastapi.staticfiles import StaticFiles

from fastapi.templating import Jinja2Templates

from pydantic import BaseModel, Field

from starlette.middleware.sessions import SessionMiddleware

from bci_iot import __version__

from bci_iot.accounts.access_db import AccessDatabase

from bci_iot.accounts.gender import hello_line, welcome_back, welcome_new

from bci_iot.accounts.security import password_strength

from bci_iot.accounts.timefmt import format_access_it

from bci_iot.accounts.store import ProfileStore, UserProfile

WEB_DIR = Path(__file__).resolve().parent

TEMPLATES = Jinja2Templates(directory=str(WEB_DIR / "templates"))
TEMPLATES.env.filters["it_time"] = format_access_it

class RegisterRequest(BaseModel):

    username: str = Field(min_length=1, max_length=64)
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
    phone_label: str = ""
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
            phone_label=profile.phone_label,
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

def create_app(

    data_dir: Path | str | None = None,
    *,
    session_secret: str | None = None,
    db_path: Path | str | None = None,
    admin_username: str | None = None,
    admin_password: str | None = None,

) -> FastAPI:

    """Application factory used by uvicorn and tests."""
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
    elif data_dir is not None or env_data:
        base = Path(data_dir) if data_dir is not None else data_root
        profiles_dir = base / "profiles"
        sqlite_path = Path(db_path) if db_path else base / "accessi.db"
    else:
        profiles_dir = data_root / "profiles"
        sqlite_path = Path(db_path) if db_path else data_root / "accessi.db"
    store = ProfileStore(profiles_dir)
    access_db = AccessDatabase(sqlite_path)
    secret = session_secret or os.getenv("BCI_IOT_SESSION_SECRET") or secrets.token_hex(32)
    admin_user = (admin_username or os.getenv("BCI_IOT_ADMIN_USERNAME") or "admin").strip()
    admin_pass = admin_password or os.getenv("BCI_IOT_ADMIN_PASSWORD") or "admin123"
    store.ensure_admin(admin_user, admin_pass)
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
    app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")
    photos_dir = profiles_dir.parent / "photos"
    photos_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/media/photos", StaticFiles(directory=str(photos_dir)), name="photos")
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
        return {
            "username": username,
            "is_admin": is_admin,
            "flash": _pop_flash(request),
            **extra,
        }
    def _post_auth_destination(profile: UserProfile) -> str:
        if profile.is_admin:
            return "/accessi"
        if profile.needs_anagrafica:
            return "/anagrafica"
        if profile.needs_calibration:
            return "/calibrazione"
        return "/dashboard"
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
                "message": message,
                "username": None,
                "is_admin": False,
                "flash": None,
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
            phone_label=profile.phone_label,
            headset_id=profile.headset_id,
            status="deleted" if profile.deleted_at else "active",
            photo_path=profile.photo_filename,
        )
    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}
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
        password: str = Form(...),
        headset_id: str = Form(""),
        profiles: ProfileStore = Depends(_store),
        access: AccessDatabase = Depends(_access),
    ) -> HTMLResponse:
        try:
            profiles.create_account(username, password, headset_id=headset_id)
        except ValueError as exc:
            _flash(request, str(exc), kind="error")
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
            )
        request.session["username"] = username.strip()
        _log_access(request, username=username.strip(), event="register", access=access)
        _flash(request, "Account creato. Compila i tuoi dati.", kind="ok")
        return _continue(
            request,
            next_url="/anagrafica",
            message="Account creato, un momento...",
        )
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
        if profile is None:
            _log_access(request, username=username.strip(), event="login_fail", access=access)
            if profiles.username_exists_active(username.strip()):
                _flash(
                    request,
                    "Password non corretta. Puoi recuperarla da «Password dimenticata?».",
                    kind="error",
                )
            else:
                _flash(request, "Utente e/o password errato", kind="error")
            return _continue(
                request,
                next_url="/login",
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
        return TEMPLATES.TemplateResponse(
            request,
            "recupera_password.html",
            _template_ctx(request, profiles),
        )

    @app.post("/recupera-password")
    def recover_password_submit(
        request: Request,
        username: str = Form(...),
        first_name: str = Form(...),
        last_name: str = Form(...),
        new_password: str = Form(...),
        new_password2: str = Form(...),
        profiles: ProfileStore = Depends(_store),
        access: AccessDatabase = Depends(_access),
    ) -> RedirectResponse:
        if new_password != new_password2:
            _flash(request, "Le nuove password non coincidono.", kind="error")
            return RedirectResponse("/recupera-password", status_code=303)
        try:
            profile = profiles.reset_password_by_identity(
                username,
                first_name=first_name,
                last_name=last_name,
                new_password=new_password,
            )
        except ValueError as exc:
            _flash(request, str(exc), kind="error")
            return RedirectResponse("/recupera-password", status_code=303)
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
                phone_label=phone_label,
            )
        except ValueError as exc:
            _flash(request, str(exc), kind="error")
            return RedirectResponse("/anagrafica", status_code=303)
        _sync_anagrafica_db(profile, access)
        profiles.ensure_headset_pairing(profile.username)
        _flash(
            request,
            welcome_new(
                first_name=profile.first_name,
                username=profile.username,
                gender=profile.gender,
            ),
            kind="ok",
        )
        next_url = "/dashboard" if profile.calibration_complete else "/calibrazione"
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
            ),
        )
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
        if profile.needs_calibration:
            return RedirectResponse("/calibrazione", status_code=303)
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
        content_type = (photo.content_type or "").lower()
        if content_type not in {"image/jpeg", "image/png", "image/webp"}:
            _flash(request, "Formato foto non supportato (usa JPG, PNG o WebP).", kind="error")
            return RedirectResponse("/anagrafica?edit=1", status_code=303)
        raw = await photo.read()
        if len(raw) > 2_500_000:
            _flash(request, "Foto troppo grande (max 2.5 MB).", kind="error")
            return RedirectResponse("/anagrafica?edit=1", status_code=303)
        ext = ".jpg" if "jpeg" in content_type else ".png" if "png" in content_type else ".webp"
        filename = f"{loaded.user_id}{ext}"
        dest = Path(app.state.photos_dir) / filename
        dest.write_bytes(raw)
        profiles.set_photo(loaded.username, filename)
        updated = profiles.get(loaded.username)
        if updated:
            _sync_anagrafica_db(updated, access)
        _flash(request, "Foto profilo aggiornata.", kind="ok")
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
        done = request.query_params.get("done") == "1" or profile.calibration_complete
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
                accuracy=accuracy,
            ),
        )

    @app.post("/api/calibrate/capture")
    def api_calibrate_capture(
        request: Request,
        payload: CaptureRequest,
        profiles: ProfileStore = Depends(_store),
    ) -> dict:
        username = _session_username(request)
        if not username:
            raise HTTPException(status_code=401, detail="Login required")
        sess, _profile = _calib_session_for(username, profiles)
        try:
            result = sess.capture(payload.command)
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
    def api_calibrate_finish(
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
            path, accuracy = sess.finish(models_dir=root / "models" / "users")
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
        dest = "/telefono" if not profile.needs_calibration else "/calibrazione"
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
        _flash(request, "Telefono scollegato. Nuovo codice generato.", kind="ok")
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
