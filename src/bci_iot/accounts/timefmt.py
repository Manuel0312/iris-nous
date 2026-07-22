"""Italian timezone display helpers for admin UI."""

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


def format_access_it(iso_utc: str | None) -> str:
    """Format stored UTC ISO as ``gg/mm/aaaa alle ore HH:MM`` (ora italiana)."""

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
    return f"{local.strftime('%d/%m/%Y')} alle ore {local.strftime('%H:%M')}"
