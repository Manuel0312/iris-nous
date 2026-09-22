"""Localized timezone display helpers for UI timestamps."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo

    try:
        ROME: timezone | ZoneInfo = ZoneInfo("Europe/Rome")
    except Exception:  # noqa: BLE001 — Windows without tzdata
        ROME = timezone(timedelta(hours=2))
except Exception:  # pragma: no cover
    ROME = timezone(timedelta(hours=2))

_AT = {
    "it": "alle ore",
    "en": "at",
    "es": "a las",
    "fr": "à",
    "de": "um",
    "pt": "às",
    "zh": "",
    "ja": "",
}


def format_access_it(iso_utc: str | None, lang: str | None = None) -> str:
    """Format stored UTC ISO for the UI (Europe/Rome wall clock)."""

    if not iso_utc or not str(iso_utc).strip():
        return "—"
    raw = str(iso_utc).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return str(iso_utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local = dt.astimezone(ROME)
    code = (lang or "it").strip().lower()[:2] or "it"
    day = local.strftime("%d/%m/%Y")
    hour = local.strftime("%H:%M")
    if code in {"zh", "ja"}:
        return f"{day} {hour}"
    connector = _AT.get(code, _AT["en"])
    return f"{day} {connector} {hour}"
