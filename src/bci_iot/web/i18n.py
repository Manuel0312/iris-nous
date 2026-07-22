"""Site language detection and translation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from starlette.requests import Request

SUPPORTED = ("it", "en", "fr", "de", "pt", "zh", "ja")
DEFAULT_LANG = "it"
COOKIE_NAME = "bci_iot_lang"


@dataclass(frozen=True, slots=True)
class Language:
    code: str
    name: str
    flag: str


LANGUAGES: tuple[Language, ...] = (
    Language("it", "Italiano", "🇮🇹"),
    Language("en", "English", "🇬🇧"),
    Language("fr", "Français", "🇫🇷"),
    Language("de", "Deutsch", "🇩🇪"),
    Language("pt", "Português", "🇵🇹"),
    Language("zh", "中文", "🇨🇳"),
    Language("ja", "日本語", "🇯🇵"),
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


def country_from_request(request: Request) -> str | None:
    headers = request.headers
    for key in (
        "cf-ipcountry",
        "cloudfront-viewer-country",
        "x-vercel-ip-country",
        "x-country-code",
        "x-appengine-country",
    ):
        value = (headers.get(key) or "").strip().upper()
        if value and value not in {"XX", "T1", "ZZ"}:
            return value
    return None


def detect_language(request: Request) -> str:
    """Preference order: cookie → Accept-Language → country → Italian."""
    cookie = normalize_lang(request.cookies.get(COOKIE_NAME))
    if cookie:
        return cookie
    accept = parse_accept_language(request.headers.get("accept-language"))
    if accept:
        return accept
    country = country_from_request(request)
    if country and country in COUNTRY_TO_LANG:
        return COUNTRY_TO_LANG[country]
    return DEFAULT_LANG


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
