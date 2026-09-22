"""Present support-chat messages with tutela rules + recipient translation."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

import httpx

log = logging.getLogger(__name__)

DISCLAIMER_IT = (
    "I messaggi di questa chat possono essere tradotti automaticamente. "
    "Iris Nous non garantisce l’accuratezza della traduzione e declina ogni "
    "responsabilità per fraintendimenti, errori o omissioni derivanti dalla "
    "traduzione automatica. In caso di dubbio fai riferimento al testo originale."
)


def _norm_lang(code: str | None, default: str = "it") -> str:
    return (code or default).strip().lower()[:2] or default


def translate_text(text: str, *, source: str, target: str) -> str:
    """Translate ``text`` from ``source`` to ``target`` language codes.

    Returns the original text unchanged if translation is unnecessary or fails.
    """

    src = _norm_lang(source)
    dst = _norm_lang(target)
    body = (text or "").strip()
    if not body or src == dst:
        return body
    snippet = body[:450]
    translated = _mymemory(snippet, src, dst)
    if not translated:
        translated = _libretranslate(snippet, src, dst)
    if not translated:
        return body
    if len(body) > 450:
        return f"{translated}\n…"
    return translated


def _mymemory(snippet: str, src: str, dst: str) -> str:
    url = (
        "https://api.mymemory.translated.net/get"
        f"?q={quote(snippet)}&langpair={quote(src)}|{quote(dst)}"
    )
    try:
        with httpx.Client(timeout=12.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
        translated = str((data.get("responseData") or {}).get("translatedText") or "").strip()
        if not translated or translated.lower() == snippet.lower():
            return ""
        # MyMemory sometimes returns QUOTA ERROR text
        if "mymemory" in translated.lower() and "quota" in translated.lower():
            return ""
        return translated
    except Exception as exc:  # noqa: BLE001
        log.warning("chat translate MyMemory failed (%s→%s): %s", src, dst, exc)
        return ""


def _libretranslate(snippet: str, src: str, dst: str) -> str:
    """Best-effort public LibreTranslate fallback (may be rate-limited)."""

    endpoints = (
        "https://libretranslate.com/translate",
        "https://translate.argosopentech.com/translate",
    )
    for url in endpoints:
        try:
            with httpx.Client(timeout=12.0) as client:
                resp = client.post(
                    url,
                    json={"q": snippet, "source": src, "target": dst, "format": "text"},
                    headers={"Accept": "application/json"},
                )
                if resp.status_code >= 400:
                    continue
                data = resp.json()
            translated = str(data.get("translatedText") or "").strip()
            if translated and translated.lower() != snippet.lower():
                return translated
        except Exception as exc:  # noqa: BLE001
            log.warning("chat translate LibreTranslate failed (%s): %s", url, exc)
    return ""


def present_support_messages(
    messages: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    *,
    viewer_is_admin: bool,
    viewer_lang: str,
    fallback_user_lang: str = "it",
) -> list[dict[str, Any]]:
    """Build display payloads for chat bubbles.

    Tutela rules
    ------------
    - The author always sees their own text as written (``body``), even if they
      change the site language later.
    - The counterpart sees a translation into ``viewer_lang``; the original
      remains available via ``show_original``.
    """

    lang = _norm_lang(viewer_lang)
    user_fallback = _norm_lang(fallback_user_lang)
    out: list[dict[str, Any]] = []
    for raw in messages:
        m = dict(raw)
        sender = str(m.get("sender") or "")
        body = str(m.get("body") or "")
        stored = str(m.get("body_translated") or "").strip()
        lang_dst = _norm_lang(str(m.get("lang_dst") or ""), default="")
        raw_src = str(m.get("lang_src") or "").strip()
        if sender == "admin":
            lang_src = _norm_lang(raw_src or "it")
        else:
            lang_src = _norm_lang(raw_src or user_fallback)
        mine = (viewer_is_admin and sender == "admin") or (
            (not viewer_is_admin) and sender != "admin"
        )
        if mine:
            m["display_body"] = body
            m["show_original"] = False
            m["original_body"] = body
            out.append(m)
            continue

        # Counterpart: translate into the viewer's current UI language.
        if lang_src == lang:
            display = body
        elif stored and lang_dst == lang and stored != body:
            display = stored
        else:
            display = translate_text(body, source=lang_src, target=lang)
        m["display_body"] = display or body
        m["show_original"] = bool(display and display != body)
        m["original_body"] = body
        out.append(m)
    return out
