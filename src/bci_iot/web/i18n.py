"""Site language detection and translation helpers."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from ipaddress import ip_address
from typing import Any
from urllib.parse import quote

import httpx
from starlette.requests import Request

SUPPORTED = ("it", "en", "es", "fr", "de", "pt", "zh", "ja")
DEFAULT_LANG = "it"
COOKIE_NAME = "bci_iot_lang"

log = logging.getLogger(__name__)

# IP → (country_code, expires_monotonic)
_IP_COUNTRY_CACHE: dict[str, tuple[str, float]] = {}
_IP_CACHE_TTL_S = 60 * 60 * 24  # 24h


@dataclass(frozen=True, slots=True)
class Language:
    code: str
    name: str
    flag: str
    flag_iso: str  # ISO country for local SVG flag (emoji often missing on Windows)

    @property
    def flag_src(self) -> str:
        return f"/flags/{self.flag_iso}.svg"


LANGUAGES: tuple[Language, ...] = (
    Language("it", "Italiano", "🇮🇹", "it"),
    Language("en", "English", "🇬🇧", "gb"),
    Language("es", "Español", "🇪🇸", "es"),
    Language("fr", "Français", "🇫🇷", "fr"),
    Language("de", "Deutsch", "🇩🇪", "de"),
    Language("pt", "Português", "🇵🇹", "pt"),
    Language("zh", "中文", "🇨🇳", "cn"),
    Language("ja", "日本語", "🇯🇵", "jp"),
)

LANGUAGE_BY_CODE = {lang.code: lang for lang in LANGUAGES}

# Country (ISO 3166-1 alpha-2) → default site language.
COUNTRY_TO_LANG: dict[str, str] = {
    "IT": "it",
    "SM": "it",
    "VA": "it",
    "FR": "fr",
    "MC": "fr",
    "BE": "fr",
    "LU": "fr",
    "CH": "de",
    "DE": "de",
    "AT": "de",
    "LI": "de",
    "ES": "es",
    "MX": "es",
    "AR": "es",
    "CO": "es",
    "CL": "es",
    "PE": "es",
    "VE": "es",
    "EC": "es",
    "UY": "es",
    "PY": "es",
    "BO": "es",
    "CR": "es",
    "PA": "es",
    "GT": "es",
    "HN": "es",
    "NI": "es",
    "SV": "es",
    "DO": "es",
    "CU": "es",
    "PR": "es",
    "PT": "pt",
    "BR": "pt",
    "AO": "pt",
    "MZ": "pt",
    "CV": "pt",
    "CN": "zh",
    "TW": "zh",
    "HK": "zh",
    "MO": "zh",
    "SG": "zh",
    "JP": "ja",
    "US": "en",
    "GB": "en",
    "UK": "en",
    "IE": "en",
    "AU": "en",
    "NZ": "en",
    "CA": "en",
    "IN": "en",
    "ZA": "en",
}


def normalize_lang(code: str | None) -> str | None:
    if not code:
        return None
    raw = code.strip().lower().replace("_", "-")
    primary = raw.split("-", 1)[0]
    if primary == "zh":
        return "zh"
    if primary in SUPPORTED:
        return primary
    return None


def parse_accept_language(header: str | None) -> str | None:
    if not header:
        return None
    parts: list[tuple[float, str]] = []
    for item in header.split(","):
        item = item.strip()
        if not item:
            continue
        if ";q=" in item:
            tag, q_raw = item.split(";q=", 1)
            try:
                q = float(q_raw.strip())
            except ValueError:
                q = 0.0
        else:
            tag, q = item, 1.0
        lang = normalize_lang(tag)
        if lang:
            parts.append((q, lang))
    if not parts:
        return None
    parts.sort(key=lambda pair: pair[0], reverse=True)
    return parts[0][1]


def detect_language(request: Request) -> str:
    """Preference: explicit cookie/session → country (geo) → Accept-Language → fallback.

    Geo wins over the browser language so an Italian visitor with an English OS
    still gets Italian. Unknown countries / unsupported Accept-Language → English.
    """
    cookie = normalize_lang(request.cookies.get(COOKIE_NAME))
    if cookie:
        return cookie
    try:
        session_lang = normalize_lang(str(request.session.get("lang") or ""))
    except Exception:
        session_lang = None
    if session_lang:
        return session_lang

    path = request.url.path if hasattr(request, "url") else ""
    # Skip IP geo on static assets (headers still used if present).
    use_ip_geo = not str(path or "").startswith(
        ("/static", "/flags", "/media", "/favicon", "/health")
    )
    country = country_from_request(request, allow_ip_lookup=use_ip_geo)
    if country:
        return COUNTRY_TO_LANG.get(country, "en")

    accept = parse_accept_language(request.headers.get("accept-language"))
    if accept:
        return accept
    # Browser sent only unsupported languages (pl, nl, …) → English
    raw_accept = (request.headers.get("accept-language") or "").strip()
    if raw_accept:
        return "en"
    return DEFAULT_LANG


def country_from_request(request: Request, *, allow_ip_lookup: bool = True) -> str | None:
    """Country from CDN/proxy headers, then optional IP geolocation (cached)."""

    headers = request.headers
    for key in (
        "cf-ipcountry",
        "cloudfront-viewer-country",
        "x-vercel-ip-country",
        "x-country-code",
        "x-appengine-country",
        "x-render-request-country",
    ):
        value = (headers.get(key) or "").strip().upper()
        if value and value not in {"XX", "T1", "ZZ"}:
            return value
    if not allow_ip_lookup:
        return None
    ip = client_ip_from_request(request)
    if not ip:
        return None
    return country_from_ip(ip)


def client_ip_from_request(request: Request) -> str | None:
    """Best-effort public client IP (Render/Cloudflare use X-Forwarded-For)."""

    for key in ("cf-connecting-ip", "true-client-ip", "x-real-ip"):
        raw = (request.headers.get(key) or "").strip()
        if raw and _is_public_ip(raw):
            return raw
    xff = (request.headers.get("x-forwarded-for") or "").strip()
    if xff:
        for part in xff.split(","):
            candidate = part.strip()
            if _is_public_ip(candidate):
                return candidate
    host = getattr(request.client, "host", None) if request.client else None
    if host and _is_public_ip(host):
        return host
    return None


def _is_public_ip(value: str) -> bool:
    try:
        addr = ip_address(value.strip())
    except ValueError:
        return False
    return not (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    )


def country_from_ip(ip: str) -> str | None:
    """Resolve ISO country for ``ip`` via free lookup APIs (in-memory cache)."""

    cached = _IP_COUNTRY_CACHE.get(ip)
    now = time.monotonic()
    if cached and cached[1] > now:
        return cached[0] or None
    country = _lookup_ip_country(ip) or ""
    _IP_COUNTRY_CACHE[ip] = (country, now + _IP_CACHE_TTL_S)
    if len(_IP_COUNTRY_CACHE) > 4000:
        stale = [k for k, (_, exp) in _IP_COUNTRY_CACHE.items() if exp <= now]
        for k in stale[:1000]:
            _IP_COUNTRY_CACHE.pop(k, None)
    return country or None


def _lookup_ip_country(ip: str) -> str | None:
    # Keep this fast: middleware runs on every HTML request.
    endpoints = (
        (f"https://get.geojs.io/v1/ip/country/{quote(ip)}.json", "geojs"),
        (f"https://ipapi.co/{quote(ip)}/country_code/", "ipapi"),
        (f"http://ip-api.com/json/{quote(ip)}?fields=status,countryCode", "ipapi_http"),
    )
    for url, kind in endpoints:
        try:
            with httpx.Client(timeout=1.2, follow_redirects=True) as client:
                resp = client.get(url, headers={"User-Agent": "IrisNous/1.0"})
            if resp.status_code >= 400:
                continue
            if kind == "geojs":
                data = resp.json()
                code = str(data.get("country") or data.get("country_code") or "").upper()
            elif kind == "ipapi_http":
                data = resp.json()
                if str(data.get("status") or "") != "success":
                    continue
                code = str(data.get("countryCode") or "").upper()
            else:
                code = (resp.text or "").strip().upper()[:2]
            if len(code) == 2 and code.isalpha() and code not in {"XX", "T1", "ZZ"}:
                return code
        except Exception as exc:  # noqa: BLE001
            log.debug("ip country lookup failed (%s): %s", url, exc)
    return None


def language_for_country(country_code: str | None) -> str:
    """Public helper: ISO country → site language (unknown → English)."""
    code = (country_code or "").strip().upper()
    if not code or code in {"XX", "T1", "ZZ"}:
        return "en"
    return COUNTRY_TO_LANG.get(code, "en")


def set_request_language(request: Request, lang: str) -> str:
    code = normalize_lang(lang) or DEFAULT_LANG
    request.state.lang = code
    request.session["lang"] = code
    return code


def get_request_language(request: Request) -> str:
    lang = getattr(request.state, "lang", None)
    if isinstance(lang, str) and lang in SUPPORTED:
        return lang
    return detect_language(request)


def translate(lang: str, message: str, **kwargs: Any) -> str:
    """Translate a message id (Italian source text or key)."""
    from bci_iot.web.translations import CATALOG

    if not message:
        return message
    code = normalize_lang(lang) or DEFAULT_LANG
    if code == DEFAULT_LANG:
        text = message
    else:
        text = CATALOG.get(code, {}).get(message, message)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError, IndexError):
            return text
    return text


def make_translator(lang: str):
    def t(message: str, **kwargs: Any) -> str:
        return translate(lang, message, **kwargs)

    return t
