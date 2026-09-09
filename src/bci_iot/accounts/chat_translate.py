"""Best-effort automatic translation for support chat (MyMemory, no API key)."""

from __future__ import annotations

import logging
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
    # MyMemory free endpoint; keep payload small.
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
