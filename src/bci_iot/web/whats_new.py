"""What's New / Novità — release notes shown in the site popup."""

from __future__ import annotations

from bci_iot import __version__

# Italian source strings (also used as i18n keys via t()).
WHATS_NEW_INTRO = (
    "Ogni aggiornamento spiega prima il problema che risolve, "
    "poi cosa è cambiato. Così capisci subito a cosa si riferisce."
)

# Newest first. Each entry: (title, problem, fix) — always problem → improvement.
WHATS_NEW_HISTORY: tuple[dict[str, object], ...] = (
    {
        "version": "0.4.4",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Novità più chiare",
                "Nelle Novità si leggeva solo il risultato, senza capire quale problema risolveva l’aggiornamento.",
                "Ora ogni voce indica prima il problema, poi la miglioria apportata.",
            ),
            (
                "Chatta con noi come una chat vera",
                "Dopo aver inviato un messaggio bisognava di nuovo compilare tutto il form per scrivere altro.",
                "Con la chat aperta hai barra e Invio come una chat normale; con Termina conversazione la chiudi e poi ne apri una nuova dal form.",
            ),
            (
                "Storico chat nel profilo",
                "Non c’era un posto chiaro per rivedere le conversazioni aperte e quelle già chiuse.",
                "In Le mie chat trovi lo storico completo e puoi rileggere ogni conversazione.",
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
                "Barra messaggio e Invio nella conversazione aperta; Termina conversazione per chiuderla e aprirne una nuova dal form.",
            ),
            (
                "Storico chat nel profilo",
                "Le chat passate non erano facili da ritrovare.",
                "In Le mie chat vedi conversazioni aperte e chiuse e le rileggi quando vuoi.",
            ),
        ),
    },
    {
        "version": "0.4.2",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Telefono con prefisso, al posto giusto",
                "In iscrizione mancava il prefisso e il numero finiva nel posto sbagliato (etichetta o cuffie).",
                "Prefisso e numero (opzionali) in iscrizione e profilo, salvati nei campi telefono corretti.",
            ),
            (
                "Una sola foto profilo",
                "Nell’anagrafica sembravano due foto da caricare.",
                "Resta una sola anteprima: scegli o cambia la foto senza doppie immagini.",
            ),
            (
                "Gli account restano dopo il deploy",
                "A ogni aggiornamento del sito online sparivano tutti gli account.",
                "I profili restano salvati; si eliminano solo con Elimina account (admin o utente).",
            ),
            (
                "Novità: anche le versioni precedenti",
                "Si vedeva solo l’ultima versione, senza lo storico degli aggiornamenti.",
                "In Novità compare l’ultima release; con Versioni precedenti scorri quelle passate.",
            ),
        ),
    },
    {
        "version": "0.4.1",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Chatta con noi, pensata per il telefono",
                "Su telefono la pagina Chatta era lunga e confusa: bisognava scorrere molto.",
                "Sul telefono vedi subito il form; riaprire o recuperare il codice resta a un tocco.",
            ),
            (
                "Novità che non copre più il menu",
                "Il tasto Novità si accavallava al nome Iris e Chiudi restava sotto il menu.",
                "Novità non si sovrappone più al brand; il popup sta sopra e si chiude senza problemi.",
            ),
        ),
    },
    {
        "version": "0.4.0",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "La chat ti parla nella tua lingua",
                "I messaggi di supporto e le email di risposta non seguivano sempre la lingua dello schermo.",
                "Chatta con noi e le email di risposta si adattano alla lingua con cui guardi Iris; l’originale resta disponibile.",
            ),
            (
                "Apri Iris e trovi subito la lingua giusta",
                "In Italia il sito poteva aprirsi in inglese se telefono o computer erano in inglese.",
                "In Italia Iris preferisce l’italiano; altri Paesi seguono la mappa delle lingue supportate.",
            ),
            (
                "Le notifiche admin si aprono al primo tocco",
                "A volte la lista admin si ricaricava e la chat non si apriva al primo tap.",
                "Quando tocchi un messaggio, entri davvero nella conversazione.",
            ),
            (
                "Moderazione più semplice per l’admin",
                "Sospendere o eliminare un account non era chiaro e pratico.",
                "Dal pannello puoi sospendere per un periodo o eliminare in modo definitivo, con passaggi pensati per la tutela.",
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
