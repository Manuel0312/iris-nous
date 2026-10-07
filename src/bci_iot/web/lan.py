"""Detect LAN addresses so phones can open Iris on the same Wi‑Fi."""

from __future__ import annotations

import os
import socket
from urllib.parse import urlparse


def _is_loopback_host(host: str) -> bool:
    h = (host or "").strip().lower().split("%")[0]
    return h in {"127.0.0.1", "localhost", "::1", "0.0.0.0"}


def list_lan_ipv4() -> list[str]:
    """Best-effort list of non-loopback IPv4 addresses on this machine."""
    found: list[str] = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if ip and not ip.startswith("127.") and ip not in found:
                found.append(ip)
    except OSError:
        pass
    # UDP trick: discover the interface used toward the internet (no packets sent).
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            if ip and not ip.startswith("127.") and ip not in found:
                found.insert(0, ip)
    except OSError:
        pass
    return found


def preferred_lan_ipv4() -> str:
    ips = list_lan_ipv4()
    return ips[0] if ips else ""


def public_site_url(request_base: str) -> str:
    """URL that phones can open.

    Priority:
    1. ``BCI_IOT_PUBLIC_URL`` if set (Render / explicit LAN)
    2. Request host when it is already a LAN / public host
    3. Auto-detected LAN IP when the request is localhost
    """
    configured = (os.getenv("BCI_IOT_PUBLIC_URL") or "").strip().rstrip("/")
    if configured:
        return configured

    base = (request_base or "").strip().rstrip("/")
    parsed = urlparse(base if "://" in base else f"http://{base}")
    host = parsed.hostname or ""
    port = parsed.port
    scheme = parsed.scheme or "http"

    if host and not _is_loopback_host(host):
        return base

    lan = preferred_lan_ipv4()
    if not lan:
        return base or "http://127.0.0.1:8000"
    netloc = f"{lan}:{port}" if port else lan
    return f"{scheme}://{netloc}"


def pairing_deep_link(*, public_base: str, code: str) -> str:
    """Link for QR: login (if needed) then open pairing with code."""
    base = public_base.rstrip("/")
    code = (code or "").strip()
    # /p/<code> handles login redirect + one-tap confirm.
    return f"{base}/p/{code}"
