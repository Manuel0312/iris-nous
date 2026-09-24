"""Present support-chat messages with tutela rules + auto translation."""

from __future__ import annotations

import json
import logging
import re
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

_SUPPORTED = ("it", "en", "es", "fr", "de", "pt", "zh", "ja")

_CLUES: dict[str, tuple[str, ...]] = {
    "fr": (
        " je ",
        " j'",
        " pas ",
        " avec ",
        " pour ",
        " casque ",
        " problème ",
        " arrive ",
        " n'arrive ",
        " comment ",
        " ça va",
        " ca va",
    ),
    "pt": (
        " não ",
        " voce ",
        " você ",
        " com ",
        " problema ",
        " fone ",
        " consigo ",
        " auscultador",
        " como vai",
        " tudo bem",
    ),
    "es": (
        " no ",
        " con ",
        " problema ",
        " auricular",
        " gracias ",
        " puedo ",
        " asociar ",
        " cómo estás",
        " como estas",
        " hola ",
    ),
    "de": (
        " ich ",
        " nicht ",
        " und ",
        " kopfhörer",
        " problem ",
        " kann ",
        " koppeln ",
        " wie geht",
        " hallo ",
    ),
    "it": (
        " non ",
        " cuffia",
        " problema ",
        " grazie ",
        " riesco ",
        " associare ",
        " telefono ",
        " come stai",
        " ciao ",
    ),
    "en": (
        " the ",
        " and ",
        " cannot ",
        " can't ",
        " with ",
        " headphone",
        " headset",
        " associate ",
        " please ",
        " help ",
        " phone ",
        " doesn't ",
        " don't ",
        " how are you",
        " are you",
        " what is",
        " what's",
        " thank you",
        " thanks ",
    ),
}


def _norm_lang(code: str | None, default: str = "it") -> str:
    raw = (code or default).strip().lower().replace("_", "-")
    if raw in {"auto", "autodetect", "detect"}:
        return "auto"
    primary = raw.split("-", 1)[0][:2]
    return primary or default


def _score_language(body: str) -> dict[str, int]:
    lowered = f" {body.lower()} "
    tokens = {w.strip(".,!?;:\"'").lower() for w in body.split()}
    scores = {lang: sum(1 for c in words if c in lowered) for lang, words in _CLUES.items()}
    if tokens & {"hi", "hello", "hey", "yo"}:
        scores["en"] = scores.get("en", 0) + 2
    if "how" in tokens and "are" in tokens:
        scores["en"] = scores.get("en", 0) + 2
    if "you" in tokens and len(tokens) <= 6:
        scores["en"] = scores.get("en", 0) + 1
    return scores


def detect_message_language(text: str, *, hint: str = "") -> str:
    """Detect chat language from text; hint is only a weak fallback."""

    body = (text or "").strip()
    hinted = _norm_lang(hint, default="")
    if not body:
        return hinted if hinted in _SUPPORTED else "en"
    if re.search(r"[\u3040-\u30ff\u3400-\u9fff]", body):
        return (
            "zh"
            if re.search(r"[\u4e00-\u9fff]", body) and not re.search(r"[\u3040-\u30ff]", body)
            else "ja"
        )
    scores = _score_language(body)
    best = max(scores, key=scores.get)
    best_score = scores[best]
    # Body evidence beats a wrong UI/lang_src hint (common bug: EN text saved as it).
    if best_score > 0:
        if hinted not in _SUPPORTED or best_score >= scores.get(hinted, 0):
            return best
        if best != hinted and best_score >= 1:
            return best
    if hinted in _SUPPORTED and best_score == 0:
        return hinted
    if best_score > 0:
        return best
    return "en"


def translate_text(text: str, *, source: str, target: str) -> str:
    """Translate ``text`` from ``source`` to ``target`` (``auto`` allowed)."""

    dst = _norm_lang(target)
    body = (text or "").strip()
    if not body:
        return body
    src = _norm_lang(source, default="auto")
    if src == "auto":
        src = detect_message_language(body, hint="")
    if src == dst:
        guessed = detect_message_language(body, hint="")
        if guessed == dst:
            return body
        src = guessed
    snippet = body[:450]
    engines = (
        lambda: _google_clients5(snippet, src, dst),
        lambda: _mymemory(snippet, src, dst),
        lambda: _mymemory(snippet, "Autodetect", dst),
        lambda: _google_clients5(snippet, "auto", dst),
        lambda: _libretranslate(snippet, src, dst),
        lambda: _libretranslate(snippet, "auto", dst),
    )
    for run in engines:
        try:
            translated = (run() or "").strip()
        except Exception as exc:  # noqa: BLE001
            log.warning("chat translate engine error: %s", exc)
            translated = ""
        if translated and translated.lower() != snippet.lower():
            if len(body) > 450:
                return f"{translated}\n…"
            return translated
    return body


def _mymemory_detect(snippet: str) -> str:
    url = (
        "https://api.mymemory.translated.net/get"
        f"?q={quote(snippet)}&langpair={quote('Autodetect|en')}"
    )
    try:
        with httpx.Client(timeout=8.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
        detected = str(
            ((data.get("responseData") or {}).get("detectedLanguage") or {})
            or data.get("detectedLanguage")
            or ""
        ).strip().lower()[:2]
        if detected in _SUPPORTED:
            return detected
        for match in data.get("matches") or []:
            mid = str(match.get("id") or "")
            if "-" in mid:
                left = mid.split("-", 1)[0].lower()[:2]
                if left in _SUPPORTED:
                    return left
    except Exception as exc:  # noqa: BLE001
        log.warning("chat lang detect failed: %s", exc)
    return ""


def _mymemory(snippet: str, src: str, dst: str) -> str:
    pair_src = "Autodetect" if src.lower() in {"auto", "autodetect"} else src
    url = (
        "https://api.mymemory.translated.net/get"
        f"?q={quote(snippet)}&langpair={quote(pair_src)}|{quote(dst)}"
    )
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
        translated = str((data.get("responseData") or {}).get("translatedText") or "").strip()
        if not translated or translated.lower() == snippet.lower():
            return ""
        if "mymemory" in translated.lower() and "quota" in translated.lower():
            return ""
        return translated
    except Exception as exc:  # noqa: BLE001
        log.warning("chat translate MyMemory failed (%s→%s): %s", src, dst, exc)
        return ""


def _google_clients5(snippet: str, src: str, dst: str) -> str:
    sl = "auto" if src.lower() in {"auto", "autodetect", ""} else src
    url = (
        "https://clients5.google.com/translate_a/t"
        f"?client=dict-chrome-ex&sl={quote(sl)}&tl={quote(dst)}&q={quote(snippet)}"
    )
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    ),
                    "Accept": "*/*",
                },
            )
            if resp.status_code >= 400:
                return ""
            data = resp.json()
        translated = _parse_google_payload(data)
        if translated and translated.lower() != snippet.lower():
            return translated
    except Exception as exc:  # noqa: BLE001
        log.warning("chat translate Google failed (%s→%s): %s", src, dst, exc)
    return ""


def _parse_google_payload(data: Any) -> str:
    """Parse clients5 / translate_a JSON into plain text."""

    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return data.strip()
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, str):
            return first.strip()
        if isinstance(first, list):
            parts: list[str] = []
            for chunk in data:
                if isinstance(chunk, list) and chunk and isinstance(chunk[0], str):
                    parts.append(chunk[0])
                elif isinstance(chunk, str):
                    parts.append(chunk)
            return "".join(parts).strip()
    return ""


def _libretranslate(snippet: str, src: str, dst: str) -> str:
    endpoints = (
        "https://libretranslate.com/translate",
        "https://translate.argosopentech.com/translate",
    )
    source = "auto" if src in {"auto", "Autodetect"} else src
    for url in endpoints:
        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                resp = client.post(
                    url,
                    json={"q": snippet, "source": source, "target": dst, "format": "text"},
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

    Tutela
    ------
    - Author always sees original ``body``.
    - Counterpart always sees ``viewer_lang`` (AI translate when needed).
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
        hint = raw_src or (user_fallback if sender != "admin" else "it")
        lang_src = detect_message_language(body, hint=hint)
        mine = (viewer_is_admin and sender == "admin") or (
            (not viewer_is_admin) and sender != "admin"
        )
        if mine:
            m["display_body"] = body
            m["show_original"] = False
            m["original_body"] = body
            out.append(m)
            continue

        if stored and lang_dst == lang and stored != body:
            display = stored
        else:
            display = translate_text(body, source=lang_src, target=lang)
            if display == body and lang_src != lang:
                display = translate_text(body, source="auto", target=lang)
        m["display_body"] = display or body
        m["show_original"] = bool(display and display != body)
        m["original_body"] = body
        out.append(m)
    return out


def resolve_support_recipient_lang(
    *,
    thread_user_lang: str = "",
    messages: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None = None,
) -> str:
    """Pick the language for email/chat delivery to the end user."""

    stored = _norm_lang(thread_user_lang, default="")
    for raw in reversed(list(messages or ())):
        if str(raw.get("sender") or "") == "admin":
            continue
        body = str(raw.get("body") or "").strip()
        if not body:
            continue
        detected = detect_message_language(body, hint=stored or "en")
        # Prefer what they write when it clearly differs from a wrong UI hint.
        if detected in _SUPPORTED:
            return detected
    if stored in _SUPPORTED:
        return stored
    return "en"