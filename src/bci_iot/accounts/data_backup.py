"""Persist Iris account data across Render redeploys via GitHub.

Free Render instances wipe ``/data`` on every deploy. When a GitHub token is
configured (same as mail: ``BCI_IOT_GITHUB_MAIL_TOKEN``), we keep an
**encrypted** bundle of ``accessi.db`` + ``photos/`` on a dedicated branch
(``iris-data``) so accounts survive without triggering another deploy of
``main``. Admin delete remains the only intentional account removal.

Critical safety: never upload an admin-only / empty DB over a richer remote
bundle (that was wiping real user accounts after failed restores).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import io
import json
import logging
import os
import sqlite3
import tarfile
import tempfile
import threading
import time
from pathlib import Path
from urllib import error, request

logger = logging.getLogger(__name__)

BUNDLE_PATH = ".iris-runtime/data-bundle.iris"
_MAGIC = b"IRIS1"
_backup_lock = threading.Lock()
_backup_timer: threading.Timer | None = None
_last_backup_at = 0.0
_state: dict[str, object] = {
    "enabled": False,
    "boot_restored": False,
    "boot_detail": "",
    "last_backup_ok": None,
    "last_backup_at": "",
    "last_error": "",
    "upload_blocked": False,
}


def _repo() -> str:
    return (
        os.getenv("BCI_IOT_GITHUB_MAIL_REPO", "").strip()
        or os.getenv("BCI_IOT_DATA_BACKUP_REPO", "").strip()
        or "Manuel0312/iris-nous"
    )


def _token_from_messaging_file() -> str:
    """Same GitHub token the mail relay may keep in /data/messaging.json."""
    roots: list[Path] = []
    env_data = os.getenv("BCI_IOT_DATA_DIR", "").strip()
    if env_data:
        roots.append(Path(env_data))
    roots.append(Path(__file__).resolve().parents[3] / "data")
    for root in roots:
        path = root / "messaging.json"
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            token = str(data.get("github_mail_token") or "").strip()
            if token:
                return token
    return ""


def _token() -> str:
    return (
        os.getenv("BCI_IOT_DATA_BACKUP_TOKEN", "").strip()
        or os.getenv("BCI_IOT_GITHUB_MAIL_TOKEN", "").strip()
        or _token_from_messaging_file()
    )


def _secret() -> str:
    return (
        os.getenv("BCI_IOT_DATA_BACKUP_KEY", "").strip()
        or os.getenv("BCI_IOT_SESSION_SECRET", "").strip()
        or _token()
    )


def _branch() -> str:
    return (os.getenv("BCI_IOT_DATA_BACKUP_BRANCH", "").strip() or "iris-data")


def _looks_like_hosted() -> bool:
    """Render/Free online: env may omit BCI_IOT_ENV=production even when live."""
    env = (os.getenv("BCI_IOT_ENV") or "").lower()
    if env in {"prod", "production"}:
        return True
    if os.getenv("RENDER") or os.getenv("RENDER_SERVICE_ID"):
        return True
    public = (os.getenv("BCI_IOT_PUBLIC_URL") or "").lower()
    if "onrender.com" in public:
        return True
    return False


def _enabled() -> bool:
    flag = os.getenv("BCI_IOT_DATA_BACKUP", "").strip().lower()
    if flag in {"0", "false", "no", "off"}:
        return False
    if not (_token() and _secret()):
        return False
    # Explicit on, hosted Render, or any non-dev environment with a token.
    if flag in {"1", "true", "yes", "on"}:
        return True
    if _looks_like_hosted():
        return True
    env = (os.getenv("BCI_IOT_ENV") or "").lower()
    return env not in {"", "dev", "development", "test", "local"}


def backup_status(*, data_root: Path | str | None = None) -> dict[str, object]:
    """Admin-facing snapshot of persistence health."""
    root = Path(data_root) if data_root else None
    users = _count_users(root) if root else 0
    return {
        "enabled": _enabled(),
        "configured_token": bool(_token()),
        "configured_key": bool(_secret()),
        "branch": _branch(),
        "bundle_path": BUNDLE_PATH,
        "boot_restored": bool(_state.get("boot_restored")),
        "boot_detail": str(_state.get("boot_detail") or ""),
        "upload_blocked": bool(_state.get("upload_blocked")),
        "last_backup_ok": _state.get("last_backup_ok"),
        "last_backup_at": str(_state.get("last_backup_at") or ""),
        "last_error": str(_state.get("last_error") or ""),
        "local_users": users,
        "local_users_non_admin": _count_users(root, exclude_admin=True) if root else 0,
    }


def record_boot_restore(ok: bool, detail: str = "") -> None:
    _state["boot_restored"] = bool(ok)
    _state["boot_detail"] = (detail or ("restored" if ok else "not restored"))[:300]
    _state["enabled"] = _enabled()
    detail_l = (detail or "").lower()
    # No remote yet → allow the first upload. Only block when restore failed
    # against an existing/richer remote (decrypt/unpack errors, etc.).
    if ok or "no remote" in detail_l or "disabled" in detail_l:
        _state["upload_blocked"] = False
    else:
        _state["upload_blocked"] = True


def clear_upload_block_if_safe(data_root: Path | str) -> None:
    """Allow uploads again once local DB has real (non-admin) accounts."""
    if _count_users(Path(data_root), exclude_admin=True) > 0:
        _state["upload_blocked"] = False


def _keystream(key: bytes, length: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < length:
        out.extend(hashlib.sha256(key + counter.to_bytes(8, "big")).digest())
        counter += 1
    return bytes(out[:length])


def _encrypt(data: bytes, secret: str) -> bytes:
    key = hashlib.sha256(secret.encode("utf-8")).digest()
    nonce = os.urandom(16)
    stream = _keystream(key + nonce, len(data))
    ct = bytes(a ^ b for a, b in zip(data, stream))
    tag = hmac.new(key, nonce + ct, hashlib.sha256).digest()
    return _MAGIC + nonce + tag + ct


def _decrypt(blob: bytes, secret: str) -> bytes:
    if not blob.startswith(_MAGIC):
        raise ValueError("unknown backup format")
    key = hashlib.sha256(secret.encode("utf-8")).digest()
    nonce = blob[5:21]
    tag = blob[21:53]
    ct = blob[53:]
    expect = hmac.new(key, nonce + ct, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expect):
        raise ValueError("backup integrity check failed")
    stream = _keystream(key + nonce, len(ct))
    return bytes(a ^ b for a, b in zip(ct, stream))


def _api(method: str, url_path: str, payload: dict | None = None) -> dict | None:
    token = _token()
    if not token:
        return None
    url = f"https://api.github.com{url_path}"
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=body, method=method.upper())
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with request.urlopen(req, timeout=90) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else None
    except error.HTTPError as exc:
        if exc.code == 404:
            return None
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        logger.warning("data backup API %s %s failed: %s %s", method, url_path, exc.code, detail)
        _state["last_error"] = f"API {exc.code}: {detail[:120]}"
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("data backup API error: %s", exc)
        _state["last_error"] = str(exc)[:200]
        return None


def _ensure_branch(repo: str, branch: str) -> bool:
    ref = _api("GET", f"/repos/{repo}/git/ref/heads/{branch}")
    if ref and isinstance(ref.get("object"), dict):
        return True
    for base_name in ("main", "master"):
        base = _api("GET", f"/repos/{repo}/git/ref/heads/{base_name}")
        if not base or not isinstance(base.get("object"), dict):
            continue
        sha = str(base["object"].get("sha") or "")
        if not sha:
            continue
        created = _api(
            "POST",
            f"/repos/{repo}/git/refs",
            {"ref": f"refs/heads/{branch}", "sha": sha},
        )
        if created is not None:
            logger.info("data backup: created branch %s from %s", branch, base_name)
            return True
    return False


def _get_remote_meta(repo: str, *, branch: str | None = None) -> dict | None:
    br = branch or _branch()
    meta = _api("GET", f"/repos/{repo}/contents/{BUNDLE_PATH}?ref={br}")
    if meta and meta.get("content"):
        return meta
    # Legacy location on main (older builds uploaded here and triggered redeploys).
    if br != "main":
        return _api("GET", f"/repos/{repo}/contents/{BUNDLE_PATH}?ref=main")
    return None


def _pack_bundle(data_root: Path) -> bytes | None:
    data_root = Path(data_root)
    db = data_root / "accessi.db"
    if not db.is_file():
        return None
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(db, arcname="accessi.db")
        photos = data_root / "photos"
        if photos.is_dir():
            for path in sorted(photos.rglob("*")):
                if path.is_file():
                    tar.add(path, arcname=str(Path("photos") / path.relative_to(photos)))
    return buf.getvalue()


def _unpack_bundle(data_root: Path, payload: bytes) -> None:
    data_root = Path(data_root)
    data_root.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as tar:
        try:
            tar.extractall(data_root, filter=tarfile.data_filter)
        except TypeError:
            tar.extractall(data_root)


def _count_users(data_root: Path | None, *, exclude_admin: bool = False) -> int:
    if data_root is None:
        return 0
    db = Path(data_root) / "accessi.db"
    if not db.is_file():
        return 0
    try:
        with sqlite3.connect(str(db)) as conn:
            conn.row_factory = sqlite3.Row
            tables = {
                str(r[0])
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            if "users" not in tables:
                return 0
            where = "IFNULL(deleted_at, '') = ''"
            if exclude_admin:
                where += " AND IFNULL(is_admin, 0) = 0"
            row = conn.execute(f"SELECT COUNT(*) AS n FROM users WHERE {where}").fetchone()
            return int(row["n"] if row else 0)
    except sqlite3.Error:
        return 0


def _count_users_in_encrypted(enc: bytes) -> int:
    try:
        raw = _decrypt(enc, _secret())
    except Exception:
        return -1
    td = tempfile.mkdtemp()
    try:
        _unpack_bundle(Path(td), raw)
        return _count_users(Path(td))
    except Exception:
        return -1
    finally:
        # Windows may keep SQLite handles briefly; never fail the count on cleanup.
        import shutil

        shutil.rmtree(td, ignore_errors=True)


def restore_data_dir(data_root: Path | str) -> bool:
    """Download encrypted runtime bundle from GitHub if local data is empty/missing."""
    if not _enabled():
        record_boot_restore(False, "backup disabled or token/key missing")
        return False
    root = Path(data_root)
    root.mkdir(parents=True, exist_ok=True)
    repo = _repo()
    meta = _get_remote_meta(repo)
    if not meta or not meta.get("content"):
        logger.info("data backup: no remote bundle yet")
        record_boot_restore(False, "no remote bundle yet")
        return False
    try:
        enc = base64.b64decode(meta["content"])
        raw = _decrypt(enc, _secret())
    except Exception as exc:  # noqa: BLE001
        logger.warning("data backup: decrypt failed: %s", exc)
        record_boot_restore(False, f"decrypt failed: {exc}")
        return False
    local_users = _count_users(root)
    remote_users = _count_users_in_encrypted(enc)
    if local_users > 1 and remote_users >= 0 and local_users >= remote_users:
        logger.info("data backup: keep local DB (users=%s)", local_users)
        record_boot_restore(True, f"kept local ({local_users} users)")
        return True
    if local_users > 1 and remote_users >= 0 and local_users > remote_users:
        logger.info("data backup: keep richer local DB")
        record_boot_restore(True, f"kept local richer ({local_users}>{remote_users})")
        return True
    try:
        _unpack_bundle(root, raw)
        logger.info("data backup: restored bundle from GitHub (%s bytes)", len(raw))
        record_boot_restore(True, f"restored ({_count_users(root)} users)")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("data backup: restore failed: %s", exc)
        record_boot_restore(False, f"restore failed: {exc}")
        return False


def backup_data_dir(data_root: Path | str, *, force: bool = False) -> bool:
    """Upload encrypted current data bundle to GitHub (iris-data branch)."""
    if not _enabled():
        return False
    global _last_backup_at
    now = time.time()
    if not force and now - _last_backup_at < 3.0:
        return False
    with _backup_lock:
        root = Path(data_root)
        clear_upload_block_if_safe(root)
        local_users = _count_users(root)
        local_non_admin = _count_users(root, exclude_admin=True)
        packed = _pack_bundle(root)
        if not packed:
            return False
        repo = _repo()
        branch = _branch()
        _ensure_branch(repo, branch)
        meta = _api("GET", f"/repos/{repo}/contents/{BUNDLE_PATH}?ref={branch}")
        if meta is None:
            # Fall back to checking main only for refuse-overwrite, not for sha.
            legacy = _api("GET", f"/repos/{repo}/contents/{BUNDLE_PATH}?ref=main")
        else:
            legacy = None
        remote_meta = meta or legacy
        if remote_meta and remote_meta.get("content"):
            try:
                enc_remote = base64.b64decode(remote_meta["content"])
                remote_users = _count_users_in_encrypted(enc_remote)
            except Exception:
                remote_users = -1
            # Never replace a richer remote with admin-only / empty local.
            if remote_users > local_users and local_non_admin == 0:
                msg = (
                    f"refuse overwrite: local users={local_users} "
                    f"(non-admin={local_non_admin}) remote={remote_users}"
                )
                logger.warning("data backup: %s", msg)
                _state["last_error"] = msg
                _state["last_backup_ok"] = False
                _state["upload_blocked"] = True
                return False
            if bool(_state.get("upload_blocked")) and local_non_admin == 0:
                msg = "upload blocked until real accounts exist locally"
                logger.warning("data backup: %s", msg)
                _state["last_error"] = msg
                return False
        enc = _encrypt(packed, _secret())
        payload: dict[str, object] = {
            "message": "chore: persist Iris accounts (encrypted runtime data)",
            "content": base64.b64encode(enc).decode("ascii"),
            "branch": branch,
        }
        if meta and meta.get("sha"):
            payload["sha"] = meta["sha"]
        result = _api("PUT", f"/repos/{repo}/contents/{BUNDLE_PATH}", payload)
        if result is None:
            _state["last_backup_ok"] = False
            return False
        _last_backup_at = time.time()
        _state["last_backup_ok"] = True
        _state["last_backup_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        _state["last_error"] = ""
        _state["upload_blocked"] = False
        logger.info(
            "data backup: uploaded encrypted bundle (%s bytes, users=%s) → %s",
            len(enc),
            local_users,
            branch,
        )
        return True


def schedule_backup(data_root: Path | str, *, delay_s: float = 1.0, force: bool = False) -> None:
    """Debounced background backup after account writes."""
    if not _enabled():
        return
    global _backup_timer
    root = str(Path(data_root))

    def _run() -> None:
        try:
            backup_data_dir(root, force=force)
        except Exception as exc:  # noqa: BLE001
            logger.warning("data backup scheduled failed: %s", exc)
            _state["last_error"] = str(exc)[:200]
            _state["last_backup_ok"] = False

    with _backup_lock:
        if _backup_timer is not None:
            _backup_timer.cancel()
        _backup_timer = threading.Timer(delay_s, _run)
        _backup_timer.daemon = True
        _backup_timer.start()
