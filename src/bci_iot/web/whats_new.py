"""What's New / Novità — release notes shown in the site popup."""

from __future__ import annotations

from bci_iot import __version__

# Italian source strings (also used as i18n keys via t()).
WHATS_NEW_INTRO = (
    "Ecco cosa c’è di nuovo in questa versione. "
    "Piccoli cambiamenti che rendono Iris più chiara e più vicina a te."
)

# Each item: short friendly headline + one supporting sentence (iPhone-style).
# Replace this list on every version bump — it describes only the current release.
WHATS_NEW_ITEMS: tuple[tuple[str, str], ...] = (
    (
        "Chatta con noi, pensata per il telefono",
        "Sul telefono vedi subito il form per scrivere al team. "
        "Riaprire una chat o recuperare il codice resta a un tocco, senza scorrere una pagina lunga.",
    ),
    (
        "Novità che non copre più il menu",
        "Il tasto Novità non si accavalla al nome Iris, e quando apri le novità "
        "puoi chiuderle senza che il menu le nasconda.",
    ),
)


def whats_new_payload() -> dict[str, object]:
    return {
        "version": __version__,
        "intro": WHATS_NEW_INTRO,
        "entries": [{"title": t, "body": b} for t, b in WHATS_NEW_ITEMS],
    }
