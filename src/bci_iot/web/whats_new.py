"""What's New / Novità — release notes shown in the site popup."""

from __future__ import annotations

from bci_iot import __version__

# Italian source strings (also used as i18n keys via t()).
WHATS_NEW_INTRO = (
    "Ecco cosa c’è di nuovo in questa versione. "
    "Piccoli cambiamenti che rendono Iris più chiara e più vicina a te."
)

# Newest release first. Each block is one version; the first matches __version__.
WHATS_NEW_HISTORY: tuple[dict[str, object], ...] = (
    {
        "version": "0.4.3",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Chatta con noi come una chat vera",
                "Dopo il primo messaggio resti nella conversazione con barra e Invio. "
                "Quando hai finito, Termina conversazione; poi puoi aprirne una nuova dal form.",
            ),
            (
                "Storico chat nel profilo",
                "In Le mie chat trovi conversazioni aperte e chiuse, e le rileggi quando vuoi.",
            ),
        ),
    },
    {
        "version": "0.4.2",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Telefono con prefisso, al posto giusto",
                "In iscrizione e nel profilo puoi scegliere il prefisso e il numero (opzionale). "
                "Il numero non finisce più nelle cuffie né nell’etichetta sbagliata.",
            ),
            (
                "Una sola foto profilo",
                "Nell’anagrafica vedi un’unica anteprima: scegli o cambia la foto senza doppie immagini.",
            ),
            (
                "Gli account restano dopo il deploy",
                "I profili non si cancellano più a ogni aggiornamento del sito. "
                "Si eliminano solo se l’admin usa Elimina account.",
            ),
            (
                "Novità: anche le versioni precedenti",
                "Apri Novità per l’ultima versione; con un tocco puoi scorrere gli aggiornamenti delle versioni passate.",
            ),
        ),
    },
    {
        "version": "0.4.1",
        "intro": WHATS_NEW_INTRO,
        "entries": (
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
        ),
    },
    {
        "version": "0.4.0",
        "intro": WHATS_NEW_INTRO,
        "entries": (
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
        ),
    },
)


def whats_new_payload() -> dict[str, object]:
    current = WHATS_NEW_HISTORY[0]
    entries = [{"title": t, "body": b} for t, b in current["entries"]]  # type: ignore[misc]
    history = []
    for block in WHATS_NEW_HISTORY[1:]:
        history.append(
            {
                "version": block["version"],
                "intro": block["intro"],
                "entries": [{"title": t, "body": b} for t, b in block["entries"]],  # type: ignore[misc]
            }
        )
    return {
        "version": __version__,
        "intro": current["intro"],
        "entries": entries,
        "history": history,
    }
