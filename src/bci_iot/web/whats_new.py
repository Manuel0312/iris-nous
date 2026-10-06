"""What's New / Novità — release notes shown in the site popup."""

from __future__ import annotations

from bci_iot import __version__

# Italian source strings (also used as i18n keys via t()).
WHATS_NEW_INTRO = "Ecco le novità di questa versione."

# Newest first. Each entry: (title, before, after) — fused into one natural paragraph in the UI.
WHATS_NEW_HISTORY: tuple[dict[str, object], ...] = (
    {
        "version": "0.4.30",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Privacy e chiarezza demo",
                "Mancava una pagina privacy e alcuni testi di home/inizia potevano far pensare a lettura cerebrale reale o a un dispositivo medico.",
                "Ora c’è Privacy in footer, un avviso di prototipo tesi UNITO (cuffia simulata, non medico), e i testi spiegano finestre EEG pubbliche/sintetiche per la demo.",
            ),
        ),
    },
    {
        "version": "0.4.29",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Impulsi EEG reali, senza colori",
                "Gli impulsi della cuffia restavano su prior letterari e la calibrazione chiedeva ancora i quattro colori, con passi codice/telefono poco chiari.",
                "Ora gli impulsi usano finestre EEG pubbliche (PhysioNet), restano in memoria per musica e altre azioni; i colori sono tolti e i passi codice/telefono sono più semplici.",
            ),
        ),
    },
    {
        "version": "0.4.28",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Le mie chat più chiare",
                "Accanto alla richiesta di chat c’era un riquadro «Suggerimenti» sulle bolle, poco utile senza conversazioni, e Le mie chat era spoglia.",
                "Ora a destra vedi le tue chat (o un invito calmo se non ce ne sono), e la pagina Le mie chat elenca aperte/chiuse e gli avvisi in modo più ordinato.",
            ),
        ),
    },
    {
        "version": "0.4.27",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Senza verifica telefono, password più in vista",
                "Nella scheda dati c’era ancora la verifica SMS del telefono (non disponibile ora) e «Cambia password» stava in basso poco evidente.",
                "Ora la verifica telefono non compare più, e «Cambia password» è un tasto chiaro subito sotto Donna / Uomo / Non binario.",
            ),
        ),
    },
    {
        "version": "0.4.26",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Dati personali su telefono, iPad e PC",
                "La schermata dei dati era pensata soprattutto per lo schermo grande e su telefono o iPad risultava stretta o scomoda.",
                "Ora si adatta: layout a colonna sul telefono, due colonne su PC/iPad orizzontale, touch più comodi e safe-area rispettate.",
            ),
        ),
    },
    {
        "version": "0.4.25",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Titolo dati più diretto",
                "In alto c’erano titoli lunghi e «Tutto ok» al posto della verifica email.",
                "Ora compare «I tuoi dati personali» e di nuovo «Email verificata».",
            ),
        ),
    },
    {
        "version": "0.4.24",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Dati centrati in pagina",
                "La schermata anagrafica restava spostata a sinistra nello schermo largo.",
                "Ora il blocco è centrato e più stretto, allineato come nel mockup.",
            ),
        ),
    },
    {
        "version": "0.4.23",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Pagina dati come nel mockup",
                "La schermata dei dati non assomigliava ancora al disegno approvato: foto in card, troppo testo e struttura diversa.",
                "Ora è allineata al mockup: foto grande con alone, controlli accanto, un solo pannello con Come ti chiami / Come ti senti e Continua sotto.",
            ),
        ),
    },
    {
        "version": "0.4.22",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Pagina dati più quieta",
                "La schermata dei tuoi dati aveva troppo vuoto, testi un po’ duri e due blocchi che sembravano complicati.",
                "Ora la foto è grande e accanto ai controlli, i testi sono più morbidi e i campi restano gli stessi in un layout più semplice.",
            ),
        ),
    },
    {
        "version": "0.4.21",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Foto profilo più accogliente",
                "I testi della foto sembravano istruzioni da scanner e, se la foto non aveva un volto, non usciva un avviso chiaro; c’era anche troppo spazio vuoto.",
                "Ora il tono è più naturale, l’avatar è più grande, il layout è più compatto e, se manca un volto, compare un popup che chiede un’altra foto per sicurezza.",
            ),
        ),
    },
    {
        "version": "0.4.20",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Prossima canzone via impulso cuffia",
                "Il tasto Prossima canzone mandava il comando a Spotify come un click normale, senza passare dalla cuffia.",
                "Ora il click invia un impulso mentale all’agente cuffia: se è pronta lo elabora e lo memorizza, e solo allora parte l’azione Spotify, con feedback di intensità.",
            ),
        ),
    },
    {
        "version": "0.4.19",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Agente cuffia simulata con memoria",
                "La cuffia sul sito era solo un’etichetta di configurazione: non “viveva” come dispositivo (accensione, indosso, contatto, impulsi) e non ricordava nulla per i passi dopo.",
                "Ora c’è un agente cuffia: la accendi, la indossi, controlli il contatto, invii impulsi EEG simulati e salva tutto in memoria per la calibrazione e i passi successivi.",
            ),
        ),
    },
    {
        "version": "0.4.17",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Config cuffia e calibrazione più realistica",
                "La calibrazione sul sito inventava i segnali con prior letterari e mostrava un’accuratezza quasi sempre al 100% sugli stessi dati di addestramento.",
                "Ora c’è il passo Configura cuffia (simulata BrainFlow, non collegata, reale in arrivo): la cattura usa lo stream simulato quando possibile, con conto alla rovescia e stima holdout onesta; i colori restano una metafora dichiarata.",
            ),
        ),
    },
    {
        "version": "0.4.16",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Backup account sempre attivo online",
                "Anche con la mail Iris già collegata, a volte gli account sparivano al deploy perché il salvataggio automatico non partiva.",
                "Ora, sul sito online, il backup su GitHub si attiva da solo quando c’è il token della mail: gli account restano dopo Manual Deploy e si cancellano solo con Elimina.",
            ),
        ),
    },
    {
        "version": "0.4.15",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Foto utente tonda in admin",
                "Nella scheda utente admin la foto diventava un ovale allungato e si leggeva male.",
                "Ora è un cerchio fisso, ritagliato al centro come l’avatar del profilo.",
            ),
        ),
    },
    {
        "version": "0.4.14",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Foto profilo con volto e ritaglio",
                "Scegliere la foto era solo un caricamento: non potevi inquadrare il volto né scegliere quale parte usare.",
                "Ora puoi ingrandire e spostare la foto, con una guida sul volto, e salvi solo l’area tonda dell’avatar.",
            ),
        ),
    },
    {
        "version": "0.4.13",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Database persone senza pannello backup",
                "In admin si vedevano stato backup, token e Salva database ora: non serviva e confondeva.",
                "Ora Database persone mostra solo gli account. Restano finché un admin non li elimina dal tasto Elimina.",
            ),
        ),
    },
    {
        "version": "0.4.12",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Conferma email solo con il codice",
                "Nella mail di iscrizione c’era anche un pulsante Conferma, oltre al codice: funzionavano entrambi e creava confusione.",
                "Ora conta solo il codice a 6 caratteri da inserire sul sito. Il vecchio link non conferma più l’account.",
            ),
        ),
    },
    {
        "version": "0.4.11",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Account che non spariscono più al deploy",
                "Dopo iscrizione e verifica, a volte gli account sparivano e in admin non si vedevano più: sul piano free il disco si svuota e un backup sbagliato poteva sovrascrivere quello buono.",
                "Ora il salvataggio va su un branch dedicato, non sovrascrive mai un database pieno con uno quasi vuoto, e in admin c’è Database persone con tutti gli account e Salva database ora.",
            ),
        ),
    },
    {
        "version": "0.4.10",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Messaggio e Invia sotto i messaggi",
                "Nella chat aperta, Messaggio e Invia stavano sopra invece che sotto, come su WhatsApp.",
                "Ora la barra per scrivere è in basso sotto i messaggi; Termina conversazione resta subito sotto.",
            ),
        ),
    },
    {
        "version": "0.4.9",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Novità senza parole sotto il titolo",
                "Aprendo Novità, scorrendo si vedevano pezzi di testo sotto la parola Novità.",
                "Ora il titolo resta fermo in alto e solo il resto della scheda scorre.",
            ),
            (
                "Via la banda scura in alto",
                "Una barra scura attraversava tutta la home e le altre pagine.",
                "L’abbiamo tolta: in alto restano solo logo, Novità e menu, senza fascia opaca.",
            ),
        ),
    },
    {
        "version": "0.4.8",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Chat ospite solo sul tuo dispositivo",
                "A volte la stessa chat senza account appariva anche su un altro telefono o computer, solo perché c’era la stessa email in memoria.",
                "Ora si apre solo qui (con il codice o riscrivendo con la stessa email). Su un altro dispositivo usi codice o recupero email.",
            ),
            (
                "Scrivere sotto, come su WhatsApp",
                "Il tasto per mandare altri messaggi non stava sotto i messaggi, e sembrava poco una chat vera.",
                "Adesso messaggio e Invia stanno sotto la conversazione; Termina conversazione resta dove serve. Il recupero chat con codice resta sempre a disposizione.",
            ),
        ),
    },
    {
        "version": "0.4.7",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Meno confusione mentre scorri",
                "Scorrendo la pagina, le scritte passavano sotto la parola Novità e si leggevano male.",
                "Ora la barra in alto copre bene il contenuto: Novità resta chiara.",
            ),
        ),
    },
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
