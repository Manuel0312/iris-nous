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


def translate_text(text: str, *, source: str, target: str) -> str:
    """Translate ``text`` from ``source`` to ``target`` language codes.

    Returns the original text unchanged if translation is unnecessary or fails.
    """

    src = (source or "it").strip().lower()[:2] or "it"
    dst = (target or "it").strip().lower()[:2] or "it"
    body = (text or "").strip()
    if not body or src == dst:
        return body
    snippet = body[:450]
    url = (
        "https://api.mymemory.translated.net/get"
        f"?q={quote(snippet)}&langpair={quote(src)}|{quote(dst)}"
    )
    try:
        with httpx.Client(timeout=8.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
        translated = str((data.get("responseData") or {}).get("translatedText") or "").strip()
        if not translated or translated.lower() == snippet.lower():
            return body
        if len(body) > 450:
            return f"{translated}\n…"
        return translated
    except Exception as exc:  # noqa: BLE001
        log.warning("chat translate failed (%s→%s): %s", src, dst, exc)
        return body


def present_support_messages(
    messages: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    *,
    viewer_is_admin: bool,
    viewer_lang: str,
) -> list[dict[str, Any]]:
    """Build display payloads for chat bubbles.

    Tutela rules
    ------------
    - The author always sees their own text as written (``body``), even if they
      change the site language later.
    - The counterpart sees a translation into ``viewer_lang``; the original
      remains available via ``show_original``.
    """

    lang = (viewer_lang or "it").strip().lower()[:2] or "it"
    out: list[dict[str, Any]] = []
    for raw in messages:
        m = dict(raw)
        sender = str(m.get("sender") or "")
        body = str(m.get("body") or "")
        lang_src = str(m.get("lang_src") or "it").strip().lower()[:2] or "it"
        lang_dst = str(m.get("lang_dst") or "").strip().lower()[:2]
        stored = str(m.get("body_translated") or "").strip()
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
