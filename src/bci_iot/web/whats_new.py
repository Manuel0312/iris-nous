"""What's New / Novità — release notes shown in the site popup."""

from __future__ import annotations

from bci_iot import __version__

# Italian source strings (also used as i18n keys via t()).
WHATS_NEW_INTRO = "Ecco le novità di questa versione."

# Newest first. Each entry: (title, before, after) — fused into one natural paragraph in the UI.
WHATS_NEW_HISTORY: tuple[dict[str, object], ...] = (
    {
        "version": "0.4.6",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Novità più facili da leggere",
                "Prima le spiegazioni erano un po’ rigide e poco chiare.",
                "Ora sono scritte in modo più semplice, come si parla.",
            ),
            (
                "Chatta con noi, come una chat normale",
                "Dopo il primo messaggio dovevi di nuovo riempire tutto il modulo per scrivere altro.",
                "Adesso, se la chat è aperta, scrivi sotto e premi Invia. Quando hai finito, puoi chiudere la conversazione e aprirne una nuova.",
            ),
            (
                "Le tue chat nel profilo",
                "Era difficile ritrovare le chat vecchie.",
                "In Le mie chat trovi quelle aperte e quelle chiuse, e le puoi rileggere quando vuoi.",
            ),
        ),
    },
    {
        "version": "0.4.5",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Novità più chiare",
                "Si capiva poco a quale problema si riferiva ogni aggiornamento.",
                "Ora ogni voce dice cosa non andava e come l’abbiamo sistemato.",
            ),
            (
                "Chatta con noi come una chat vera",
                "Per continuare a scrivere bisognava di nuovo compilare tutto il form.",
                "Con la chat aperta hai barra e Invia; con Termina conversazione la chiudi e poi ne apri una nuova.",
            ),
            (
                "Storico chat nel profilo",
                "Non c’era un posto chiaro per rivedere le chat.",
                "In Le mie chat trovi aperte e chiuse.",
            ),
        ),
    },
    {
        "version": "0.4.4",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Novità più chiare",
                "Si leggeva solo il risultato, senza capire il problema.",
                "Ogni voce racconta cosa non andava e come l’abbiamo sistemato.",
            ),
            (
                "Chatta con noi come una chat vera",
                "Dopo un messaggio bisognava di nuovo compilare tutto il form.",
                "Con la chat aperta scrivi e invii come in una chat normale; poi puoi chiuderla e aprirne una nuova.",
            ),
            (
                "Storico chat nel profilo",
                "Le chat aperte e chiuse non erano facili da trovare.",
                "Le trovi in Le mie chat e le rileggi quando vuoi.",
            ),
        ),
    },
    {
        "version": "0.4.3",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Chatta con noi come una chat vera",
                "Dopo il primo messaggio non si poteva continuare a scrivere in modo naturale.",
                "Ora c’è la barra messaggio e Invia; puoi anche terminare la conversazione e aprirne una nuova.",
            ),
            (
                "Storico chat nel profilo",
                "Le chat passate erano difficili da ritrovare.",
                "In Le mie chat vedi aperte e chiuse.",
            ),
        ),
    },
    {
        "version": "0.4.2",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Telefono con prefisso",
                "In iscrizione non c’era il prefisso e il numero finiva nel posto sbagliato.",
                "Ora scegli prefisso e numero (se vuoi) già in iscrizione e nel profilo, nei campi giusti.",
            ),
            (
                "Una sola foto profilo",
                "Sembrava di dover caricare due foto.",
                "Ora c’è una sola anteprima.",
            ),
            (
                "Gli account restano dopo l’aggiornamento",
                "A ogni aggiornamento del sito sparivano tutti gli account.",
                "Ora restano; si cancellano solo con Elimina account.",
            ),
            (
                "Anche le versioni precedenti",
                "Si vedeva solo l’ultima novità.",
                "Con Versioni precedenti puoi leggere anche gli aggiornamenti passati.",
            ),
        ),
    },
    {
        "version": "0.4.1",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Chatta più comoda sul telefono",
                "Su telefono la pagina era lunga e confusa.",
                "Ora vedi subito dove scrivere; il resto resta a un tocco.",
            ),
            (
                "Novità e menu non si pestano i piedi",
                "Il tasto Novità si sovrapponeva a Iris e Chiudi restava sotto il menu.",
                "Ora non si accavalla più e il popup si chiude senza problemi.",
            ),
        ),
    },
    {
        "version": "0.4.0",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "La chat nella tua lingua",
                "Messaggi e email di risposta non seguivano sempre la lingua dello schermo.",
                "Ora si adattano alla lingua con cui guardi Iris; puoi sempre vedere l’originale.",
            ),
            (
                "Lingua giusta all’apertura",
                "In Italia a volte il sito si apriva in inglese.",
                "In Italia Iris parte in italiano; altrove segue le lingue supportate.",
            ),
            (
                "Notifiche admin al primo tocco",
                "A volte toccavi un messaggio e la chat non si apriva.",
                "Ora al primo tocco entri nella conversazione.",
            ),
            (
                "Moderazione più semplice",
                "Sospendere o eliminare un account era poco chiaro.",
                "Dal pannello admin puoi farlo in pochi passaggi.",
            ),
        ),
    },
)


def _entry_dicts(entries: object) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for item in entries:  # type: ignore[union-attr]
        if len(item) == 3:
            title, problem, fix = item
            out.append({"title": title, "problem": problem, "fix": fix, "body": fix})
        else:
            title, body = item
            out.append({"title": title, "problem": "", "fix": body, "body": body})
    return out


def whats_new_payload() -> dict[str, object]:
    current = WHATS_NEW_HISTORY[0]
    entries = _entry_dicts(current["entries"])
    history = []
    for block in WHATS_NEW_HISTORY[1:]:
        history.append(
            {
                "version": block["version"],
                "intro": block["intro"],
                "entries": _entry_dicts(block["entries"]),
            }
        )
    return {
        "version": __version__,
        "intro": current["intro"],
        "entries": entries,
        "history": history,
    }
