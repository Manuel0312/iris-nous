"""What's New / Novità — release notes shown in the site popup."""

from __future__ import annotations

from bci_iot import __version__

# Italian source strings (also used as i18n keys via t()).
WHATS_NEW_INTRO = (
    "Ecco cosa c’è di nuovo in questa versione. "
    "Piccoli cambiamenti che rendono Iris più chiara e più vicina a te."
)

# Each item: short friendly headline + one supporting sentence (iPhone-style).
WHATS_NEW_ITEMS: tuple[tuple[str, str], ...] = (
    (
        "La chat ti parla nella tua lingua",
        "Ora i messaggi di Chatta con noi (e le email di risposta) si adattano "
        "alla lingua con cui stai guardando Iris. Tu leggi comodo; il testo originale resta sempre disponibile.",
    ),
    (
        "Apri Iris e trovi subito la lingua giusta",
        "Se sei in Italia, il sito preferisce l’italiano anche quando il telefono "
        "o il computer sono impostati in inglese. Altri Paesi seguono la mappa delle lingue supportate.",
    ),
    (
        "Le notifiche admin si aprono al primo tocco",
        "Prima a volte la lista si ricaricava e la chat non si apriva. "
        "Ora, quando tocchi un messaggio, entri davvero nella conversazione.",
    ),
    (
        "Moderazione più semplice per l’admin",
        "Dal pannello puoi sospendere un account per un periodo oppure eliminarlo in modo definitivo, "
        "con passaggi chiari e pensati per la tutela.",
    ),
)


def whats_new_payload() -> dict[str, object]:
    return {
        "version": __version__,
        "intro": WHATS_NEW_INTRO,
        "entries": [{"title": t, "body": b} for t, b in WHATS_NEW_ITEMS],
    }
