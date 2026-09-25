"""Persist Iris account data across Render redeploys via GitHub.

Free Render instances wipe ``/data`` on every deploy. When a GitHub token is
configured (same as mail: ``BCI_IOT_GITHUB_MAIL_TOKEN``), we keep an
**encrypted** bundle of ``accessi.db`` + ``photos/`` in the repo so accounts
survive. Admin delete remains the only intentional account removal.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import io
import json
import logging
import os
import tarfile
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


def _repo() -> str:
    return (
        os.getenv("BCI_IOT_GITHUB_MAIL_REPO", "").strip()
        or os.getenv("BCI_IOT_DATA_BACKUP_REPO", "").strip()
        or "Manuel0312/iris-nous"
    )


def _token() -> str:
    return (
        os.getenv("BCI_IOT_DATA_BACKUP_TOKEN", "").strip()
        or os.getenv("BCI_IOT_GITHUB_MAIL_TOKEN", "").strip()
    )


def _secret() -> str:
    return (
        os.getenv("BCI_IOT_DATA_BACKUP_KEY", "").strip()
        or os.getenv("BCI_IOT_SESSION_SECRET", "").strip()
        or _token()
    )


def _enabled() -> bool:
    flag = os.getenv("BCI_IOT_DATA_BACKUP", "").strip().lower()
    if flag in {"0", "false", "no", "off"}:
        return False
    if flag in {"1", "true", "yes", "on"}:
        return bool(_token() and _secret())
    # Default: only production (Render), so local tests never upload.
    env = (os.getenv("BCI_IOT_ENV") or "").lower()
    if env in {"prod", "production"}:
        return bool(_token() and _secret())
    return False


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
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("data backup API error: %s", exc)
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


def _local_user_signal(data_root: Path) -> int:
    db = Path(data_root) / "accessi.db"
    if not db.is_file():
        return 0
    try:
        return max(1, db.stat().st_size)
    except OSError:
        return 0


def restore_data_dir(data_root: Path | str) -> bool:
    """Download encrypted runtime bundle from GitHub if local data is empty/missing."""
    if not _enabled():
        return False
    root = Path(data_root)
    root.mkdir(parents=True, exist_ok=True)
    repo = _repo()
    meta = _api("GET", f"/repos/{repo}/contents/{BUNDLE_PATH}")
    if not meta or not meta.get("content"):
        logger.info("data backup: no remote bundle yet")
        return False
    try:
        enc = base64.b64decode(meta["content"])
        raw = _decrypt(enc, _secret())
    except Exception as exc:  # noqa: BLE001
        logger.warning("data backup: decrypt failed: %s", exc)
        return False
    local_signal = _local_user_signal(root)
    if local_signal > 8_000 and local_signal >= len(raw) * 0.9:
        logger.info("data backup: keep local DB (size=%s)", local_signal)
        return False
    try:
        _unpack_bundle(root, raw)
        logger.info("data backup: restored bundle from GitHub (%s bytes)", len(raw))
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("data backup: restore failed: %s", exc)
        return False


def backup_data_dir(data_root: Path | str, *, force: bool = False) -> bool:
    """Upload encrypted current data bundle to GitHub."""
    if not _enabled():
        return False
    global _last_backup_at
    now = time.time()
    if not force and now - _last_backup_at < 3.0:
        return False
    with _backup_lock:
        root = Path(data_root)
        packed = _pack_bundle(root)
        if not packed:
            return False
        enc = _encrypt(packed, _secret())
        repo = _repo()
        meta = _api("GET", f"/repos/{repo}/contents/{BUNDLE_PATH}")
        sha = meta.get("sha") if meta else None
        payload = {
            "message": "chore: persist Iris accounts (encrypted runtime data)",
            "content": base64.b64encode(enc).decode("ascii"),
            "branch": "main",
        }
        if sha:
            payload["sha"] = sha
        result = _api("PUT", f"/repos/{repo}/contents/{BUNDLE_PATH}", payload)
        if result is None:
            return False
        _last_backup_at = time.time()
        logger.info("data backup: uploaded encrypted bundle (%s bytes)", len(enc))
        return True


def schedule_backup(data_root: Path | str, *, delay_s: float = 2.0) -> None:
    """Debounced background backup after account writes."""
    if not _enabled():
        return
    global _backup_timer
    root = str(Path(data_root))

    def _run() -> None:
        try:
            backup_data_dir(root)
        except Exception as exc:  # noqa: BLE001
            logger.warning("data backup scheduled failed: %s", exc)

    with _backup_lock:
        if _backup_timer is not None:
            _backup_timer.cancel()
        _backup_timer = threading.Timer(delay_s, _run)
        _backup_timer.daemon = True
        _backup_timer.start()
