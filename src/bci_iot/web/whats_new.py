"""What's New / Novità — release notes shown in the site popup."""

from __future__ import annotations

from bci_iot import __version__

# Italian source strings (also used as i18n keys via t()).
WHATS_NEW_INTRO = "Ecco le novità di questa versione."

# Newest first. Each entry: (title, before, after) — fused into one natural paragraph in the UI.
WHATS_NEW_HISTORY: tuple[dict[str, object], ...] = (
    {
        "version": "0.5.11",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "App: Chatta con noi e chat in Account",
                "Dall’app non c’era Chatta con noi né lo storico chat; lo swipe sulle foto Iris mostrava bande ai lati.",
                "In Account (da loggati): Chatta con noi e Le tue chat restano nell’app senza aprire il sito; swipe foto senza bande laterali.",
            ),
        ),
    },
    {
        "version": "0.5.10",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Chatta con noi: traduzione automatica di nuovo chiara",
                "La traduzione admin↔utente a volte non si vedeva (motori bloccati in cloud) e sembrava sparita.",
                "Ripristinata e rinforzata: badge «Tradotto automaticamente», disclaimer in evidenza, più motori di traduzione e salvataggio della traduzione per la volta dopo.",
            ),
        ),
    },
    {
        "version": "0.5.9",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Cuffia: se è spenta non è «già associata»",
                "Riapriendo l’app la cuffia risultava già associata/pronta anche spenta, saltando Accendi e Bluetooth.",
                "Ora: spenta = Da accendere; va Accendi → Associa → Indossa. I modelli SÌ/NO (impulsi) restano salvati; i tasti sono solo il modo di inviarli in demo.",
            ),
        ),
    },
    {
        "version": "0.5.8",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "App: niente crash su Connessioni, login che resta",
                "Aprendo Connessioni l’app ripartiva il servizio chiamate e su Samsung crashava (dialog cache); al riavvio sembravi sloggato.",
                "Connessioni non riavvia più i servizi; i permessi si chiedono solo da Permessi; all’avvio il token ripristina la sessione e resti collegato.",
            ),
        ),
    },
    {
        "version": "0.5.7",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "App: SÌ risponde la chiamata, tasti più distanti",
                "Premendo SÌ su una chiamata l’app riconosceva il pensiero ma non rispondeva al telefono; il tasto restava «premuto» e i bottoni erano troppo vicini.",
                "Ora il token dispositivo arriva all’app e il SÌ/NO attiva subito risposta/rifiuto OS; i tasti non restano bloccati e hanno più spazio; login più snello.",
            ),
        ),
    },
    {
        "version": "0.5.6",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "App: vetro liquido e cuffia a passi chiari",
                "La grafica era piatta; al tap compariva un rettangolo azzurro; in Associazione i tasti non rispondevano (id duplicato) e l’ordine era confuso.",
                "UI liquid glass, tap senza alone azzurro, flusso Accendi → Bluetooth → Indossa un passo alla volta; Indossa di nuovo funziona.",
            ),
        ),
    },
    {
        "version": "0.5.5",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "App Android: anteprima messaggi col SÌ",
                "I messaggi restavano solo simulati; col SÌ si apriva WhatsApp senza vedere il testo.",
                "Su Android, con «Accesso alle notifiche», Iris riceve l’anteprima WhatsApp/Telegram/SMS: col SÌ la mostra e apre l’app; il servizio resta in ascolto in background.",
            ),
        ),
    },
    {
        "version": "0.5.4",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "App: cuffia simulata come Bluetooth reale",
                "La cuffia risultava già indossata senza accensione né associazione; Spotify dall’app riportava al sito.",
                "Ora: Accendi → Cerca Bluetooth → Associa Iris → Indossa → calibra → permessi/Spotify; il collegamento Spotify torna nell’app.",
            ),
        ),
    },
    {
        "version": "0.5.3",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "App: Account senza scorrere",
                "In Account foto, dati e tasti chiedevano di scorrere per vedere tutto.",
                "Ora profilo, accesso e conferma email stanno in una sola schermata; solo «Modifica» può scorrere il form.",
            ),
        ),
    },
    {
        "version": "0.5.2",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "App: testi leggibili su ogni tema e foto",
                "Novità e ingranaggio erano bianchi su sfondi chiari; alcuni sottotitoli sparivano col tema chiaro.",
                "Ora i tasti top hanno contrasto fisso sul tema, e su Iris restano chiari sulle foto; testi secondari più scuri/chiari a seconda del tema.",
            ),
        ),
    },
    {
        "version": "0.5.1",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "App: niente «Collega telefono» se hai già l’app",
                "In Connessioni c’era ancora Telefono/PIN anche se stavi già usando l’app scaricata.",
                "Nell’app il dispositivo si collega da solo all’accesso; resta Permessi per chiamate e notifiche.",
            ),
        ),
    },
    {
        "version": "0.5.0",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "App: tutte le Connessioni restano nell’app",
                "In ascolto, Telefono, Permessi e Musica aprivano ancora pagine del sito con scroll e chrome web.",
                "Ora ogni voce di Connessioni è una schermata nativa compatta (come la cuffia): tap, niente redirect.",
            ),
        ),
    },
    {
        "version": "0.4.99",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "App: cuffia nativa, senza aprire il sito",
                "Configura cuffia apriva ancora la pagina web (Torna all’app, banner computer, tanto scroll).",
                "Ora Associazione e Calibrazione sono schermate dell’app: compatte, a tap, stessi dati del cloud.",
            ),
        ),
    },
    {
        "version": "0.4.98",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Preview locale: codice subito, senza aspettare la mail",
                "Restavi bloccato su «Conferma email» perché in locale la mail non parte e il codice non si vedeva.",
                "Ora in anteprima il codice compare in grande e si inserisce da solo; se manca, l’app lo richiede subito.",
            ),
        ),
    },
    {
        "version": "0.4.97",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Anteprima locale: codice email a schermo",
                "In preview sul computer la mail di conferma non arriva, quindi non si poteva completare l’iscrizione.",
                "In locale il codice a 6 caratteri compare nell’app (e si può copiare); online resta solo la mail vera.",
            ),
        ),
    },
    {
        "version": "0.4.96",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "App: codice email in registrazione, non dopo il login",
                "Dopo Accedi/Iscriviti si finiva sulla pagina sito «Conferma email», e il codice veniva chiesto anche aprendo la cuffia.",
                "In iscrizione il codice è subito nell’app (schermata bloccante); con account già verificato Accedi non chiede più il codice; zero redirect al sito.",
            ),
        ),
    },
    {
        "version": "0.4.95",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "App: conferma email senza uscire dal telefono",
                "Cliccando Cuffia senza aver confermato l’email, si apriva la pagina sito con menu e Novità.",
                "Ora la conferma email resta nell’overlay dell’app; dopo il codice torni a configurare la cuffia.",
            ),
        ),
    },
    {
        "version": "0.4.94",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "App: cuffia e calibrazione senza uscire dall’app",
                "Da Connessioni si finiva sul sito, e chi creava l’account solo dal telefono non aveva lo stesso percorso cuffia del PC.",
                "Ora indosso, calibrazione SÌ/NO e In ascolto restano dentro l’app (stesso account e dati del cloud); l’admin vede anche gli account creati da telefono.",
            ),
        ),
    },
    {
        "version": "0.4.93",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "App telefono: swipe fluido, Account e setup completo",
                "Lo swipe Iris lagava, Account non aveva occhio/requisiti password, e da telefono mancavano cuffia, calibrazione e permessi.",
                "Swipe più snappy; password come sul sito; Connessioni apre cuffia, In ascolto, telefono e permessi nativi.",
            ),
        ),
    },
    {
        "version": "0.4.92",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Impostazioni: testo leggibile, tendine insieme, bandiere",
                "Note poco contrastate, Tema e Lingua si chiudevano a vicenda, bandiere assenti nella lista.",
                "Pannello più opaco e testi chiari; Tema e Lingua si aprono anche insieme; bandiere con SVG + emoji di riserva.",
            ),
        ),
    },
    {
        "version": "0.4.91",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Impostazioni e tendine più fluide",
                "Aprire ingranaggio o Tema/Lingua era uno stacco netto, tipo flash.",
                "Ora pannello, backdrop e tendine entrano con una dinamica leggera e veloce (quasi 3D), senza tagli secchi.",
            ),
        ),
    },
    {
        "version": "0.4.90",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Tendine Tema/Lingua senza sovrapposizione",
                "Aprendo Tema, il menu copriva Lingua e sembrava buggato.",
                "Ora le tendine si aprono spingendo il contenuto sotto (niente overlap): una aperta alla volta, lista chiara.",
            ),
        ),
    },
    {
        "version": "0.4.89",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Tema a tendina e foto a tutto schermo",
                "Il tema era una lista di bottoni e le foto avevano bande nere sopra/sotto.",
                "Ora anche il Tema è un menu a tendina come la Lingua, e le foto Iris riempiono lo schermo (cover, centrate) senza bande.",
            ),
        ),
    },
    {
        "version": "0.4.88",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Lingua: menu a tendina vero",
                "La lista lingue si apriva come bottoni sparsi sotto, non come tendina.",
                "Ora Lingua è un selettore: tocchi, si apre il menu sotto (scrollabile), scegli e vai.",
            ),
        ),
    },
    {
        "version": "0.4.87",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Iris: swipe, foto centrate, tastiera senza zoom, rotellina",
                "Non si poteva scorrere le foto col dito, alcune erano tagliate, digitare zoomava la pagina e l’icona impostazioni sembrava un sole.",
                "Ora scorri sinistra/destra (foto e testi insieme), le foto stanno nel telefono, la tastiera non zoomma e la rotellina apre Tema e Lingua (clic su Lingua per cambiarla).",
            ),
        ),
    },
    {
        "version": "0.4.86",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "App telefono = anteprima; /app non è più la destinazione",
                "Sul telefono restava la vecchia schermata Ecosistema e /app sembrava un’altra app.",
                "Ora l’app nativa mostra la stessa UI dell’anteprima (Connessioni, Iris, Account). Sul browser /app porta all’anteprima; la shell fullscreen è solo per l’app.",
            ),
        ),
    },
    {
        "version": "0.4.85",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "App Account: dopo Salva vedi il profilo",
                "Premendo Salva restavi sul form vuoto e non vedevi i dati appena salvati.",
                "Ora dopo Salva compare una pagina chiara con nome, email, telefono e come ti senti; da lì puoi modificare o uscire.",
            ),
        ),
    },
    {
        "version": "0.4.84",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "App Account: foto e prefisso telefono",
                "La foto profilo era storta e il prefisso era un campo di testo inutile.",
                "Ora la foto è centrata e chiara (come sul sito) e scegli paese/prefisso dalla lista con bandiera, poi digiti solo il numero.",
            ),
        ),
    },
    {
        "version": "0.4.83",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "App: lingue e Novità come sul sito",
                "Cambiare lingua nell’app non traduceva i testi e mancava Novità.",
                "Ora l’app usa le stesse lingue del sito (testi tradotti) e ha il tasto Novità con lo storico versioni.",
            ),
        ),
    },
    {
        "version": "0.4.82",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Ponte PC↔cloud, gate contesti e backup più solido",
                "Il worker BCI sul PC non parlava col sito; un SÌ poteva rubare il contesto sbagliato; SQLite su Render era fragile.",
                "Ora `bci-iot run --cloud` invia SÌ/NO al hub; se arriva un messaggio durante la musica serve una conferma; il backup include cuffia e non committa a ogni riga.",
            ),
        ),
    },
    {
        "version": "0.4.81",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "App: cosa fa Iris e perché iscriversi",
                "Senza testo non si capiva a cosa serve l’app né perché creare un account.",
                "Ora su Iris c’è una card liquid glass che spiega sì/no e i collegamenti; in Account è chiaro perché registrarsi (stessi dati su sito e app).",
            ),
        ),
    },
    {
        "version": "0.4.80",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "App: glass, foto e impostazioni",
                "I testi che ruotavano ogni 7 secondi e il popup bianco non servivano.",
                "Ora su Iris restano le foto con un pill liquid glass; la rotella apre lingua (come sul sito) e aspetto chiaro, scuro o automatico in base all’ora.",
            ),
        ),
    },
    {
        "version": "0.4.79",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Anteprima di nuovo visibile",
                "Su Render restava una versione vecchia e l’anteprima poteva risultare vuota.",
                "Ora l’app è disegnata dentro il telefono (niente iframe vuoto) e basta il Manual Deploy per vedere Connessioni, Iris con le foto e Account.",
            ),
        ),
    },
    {
        "version": "0.4.78",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "App: foto del sito e account reale",
                "L’app sembrava vuota e l’Account era finto.",
                "Ora Iris usa le stesse foto del sito (poi in 3D); Account legge i cookie: se sei già entrato vedi i tuoi dati, altrimenti login o iscrizione, e le modifiche restano uguali sul sito.",
            ),
        ),
    },
    {
        "version": "0.4.77",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "App semplice con popup che ruotano",
                "L’app ripeteva il sito lungo e bisognava scorrere.",
                "Ora è una guida a schermo pieno: su Iris i popup cambiano ogni 7 secondi; in basso restano Connessioni, Iris e Account.",
            ),
        ),
    },
    {
        "version": "0.4.76",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Anteprima: tre tasti in basso",
                "La barra dell’anteprima aveva troppe sezioni.",
                "Ora solo tre: Connessioni, Iris al centro, Account con i tuoi dati.",
            ),
        ),
    },
    {
        "version": "0.4.75",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Anteprima app navigabile prima del download",
                "Per capire com’è l’app bisognava installarla sul telefono.",
                "Ora su /app/preview c’è un telefono virtuale: sito Iris, telefono, permessi e SÌ/NO, senza scaricare nulla.",
            ),
        ),
    },
    {
        "version": "0.4.74",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Testi dell’app più semplici e invitanti",
                "Nell’app restavano frasi da laboratorio («companion», simulazioni, gergo tecnico).",
                "Ora i messaggi sono brevi e chiari: entrata, telefono, permessi e prove invitano a usare Iris senza spiegoni.",
            ),
        ),
    },
    {
        "version": "0.4.73",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "App = sito completo (prima scoperta)",
                "Chi scaricava l’app vedeva un hub tecnico e non capiva Iris.",
                "Ora /app e l’app nativa aprono subito il sito principale identico (scopri, account, Ecosistema, 3D); associazione telefono resta in /app/device.",
            ),
        ),
    },
    {
        "version": "0.4.72",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "SÌ su messaggio apre WhatsApp + app come il sito",
                "Su messaggio il SÌ restava solo simulato e l’app non ripeteva i flussi del sito.",
                "Ora al SÌ Iris apre WhatsApp (senza leggere i messaggi); /app ha un ingresso chiaro sito→associa→permessi e l’app nativa mostra il sito completo in WebView.",
            ),
        ),
    },
    {
        "version": "0.4.71",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Fix: cancella tutti gli account non va più in errore",
                "Il tasto Database a volte mostrava Internal Server Error durante la cancellazione.",
                "Ora la pulizia gestisce errori parziali e porta Iris allo stato vergine senza bloccare la pagina.",
            ),
        ),
    },
    {
        "version": "0.4.70",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Admin: cancella tutti gli account dal Database",
                "Per azzerare Iris serviva uno script o chiamate API.",
                "Nella sezione Database persone c’è un tasto con conferma: elimina tutti gli utenti e lascia solo admin.",
            ),
        ),
    },
    {
        "version": "0.4.69",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Ecosistema su iPad e iPhone + reset account demo",
                "Su tablet i QR si impilavano male e su telefono proporzioni e animazione cuffia andavano strette.",
                "Ora Ecosistema si adatta meglio a iPad e smartphone; in admin si possono azzerare tutti gli account demo restando solo admin.",
            ),
        ),
    },
    {
        "version": "0.4.68",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Ecosistema: cuffia animata, store «Prossimamente» e loghi ufficiali",
                "La card cuffia era vuota, i QR non avevano una landing store e i canali usavano icone generiche con testi sproporzionati.",
                "Ora la cuffia ha un’animazione 3D, QR e tap aprono «Prossimamente in store», Spotify/Alexa/Google Assistant hanno i loghi ufficiali e i testi sono più amichevoli.",
            ),
        ),
    },
    {
        "version": "0.4.67",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Ecosistema: layout cuffia+telefono e store chiari",
                "Le tre card in fila spezzavano le proporzioni e gli store non seguivano lo stile badge chiaro.",
                "Ora cuffia e telefono sono affiancati, Spotify sotto a tutta larghezza; badge Google Play/App Store chiari con QR, Prossimamente ed emoji.",
            ),
        ),
    },
    {
        "version": "0.4.66",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Ecosistema: store Google Play / App Store e layout ampio",
                "I download erano QR semplici e la pagina restava stretta e lunga.",
                "Ora Telefono mostra badge Google Play e App Store con QR e «Prossimamente»; Ecosistema è a tre colonne su desktop.",
            ),
        ),
    },
    {
        "version": "0.4.65",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "iPhone: SÌ/NO risponde con CallKit",
                "Su iPhone non si può comandare la linea cellulare del gestore, quindi SÌ/NO restava solo contesto.",
                "Ora Iris presenta una chiamata nativa CallKit: SÌ risponde e NO rifiuta quella schermata (bypass per la demo). Su Android resta il controllo sulla linea cellulare.",
            ),
        ),
    },
    {
        "version": "0.4.64",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "SÌ/NO può rispondere o rifiutare su Android",
                "Premendo SÌ/NO Iris aggiornava solo il contesto e il telefono continuava a squillare.",
                "Ora su Android, con il permesso «Rispondi alle chiamate», SÌ/NO prova anche a rispondere o rifiutare la chiamata cellulare; su iPhone resta il limite del sistema.",
            ),
        ),
    },
    {
        "version": "0.4.63",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Ecosistema centrato, QR download e SÌ/NO dall’app",
                "I testi in Ecosistema erano decentrati; mancavano QR per scaricare l’app; SÌ/NO richiedevano la pagina In ascolto aperta sul PC.",
                "Ora Ecosistema e popup sono centrati; QR Android/iPhone verso le pagine download; l’app tiene la cuffia virtuale pronta e può inviare SÌ/NO senza tenere aperta In ascolto.",
            ),
        ),
    },
    {
        "version": "0.4.62",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Foto profilo: tasti chiari e zoom utile",
                "Con la foto già salvata restavano «Scegli una foto», il selettore file e più «Cambia foto»; lo zoom andava su estremi poco utili.",
                "Ora: senza foto solo Scegli; con foto solo Cambia; in ritaglio Cambia/Annulla/Salva; ingrandimento da Lontano a Vicino senza doppioni.",
            ),
        ),
    },
    {
        "version": "0.4.61",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Cuffia virtuale in un tap + telefono più solido",
                "Per la demo senza cuffia fisica bisognava Accendi/Indossa/Contatto a mano; l’APK perdeva lo squillo in background e i messaggi non arrivavano al contesto.",
                "Ora «Indossa cuffia virtuale» prepara la cuffia simulata come se fosse in testa; In ascolto mostra lo stato e sblocca SÌ/NO; l’APK tiene una notifica foreground per le chiamate; puoi simulare anche un messaggio verso Iris.",
            ),
        ),
    },
    {
        "version": "0.4.60",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Foto profilo senza ricaricare la pagina",
                "Salvando la foto sotto i tuoi dati la pagina si ricaricava e cancellava nome, email e altri campi già scritti; cambiare foto dal telefono era difficile.",
                "Ora la foto si salva al volo senza ricaricare; puoi cambiarla quando vuoi; la navbar in scroll sfuma il testo sotto; Ecosistema su smartphone ha tasti allineati; Chatta con noi non disturba più durante iscrizione e anagrafica.",
            ),
        ),
    },
    {
        "version": "0.4.59",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Cuffia senza riconfigurare, associazione pulita, Spotify unico",
                "Dopo la prima calibrazione la cuffia chiedeva di rifare tutto; il PIN era su una pagina pesante; Spotify sul sito e sull’app si contraddicevano e la musica del telefono non era quella di Iris.",
                "Ora cuffia pronta = solo Accendi/Indossa + Ripristina se vuoi; Ecosistema → Associazione apre codice+QR on-demand; Spotify si collega una volta sul sito e l’app lo vede; la musica attiva arriva dall’API Spotify (non dal player locale).",
            ),
            (
                "App liquid glass + QR",
                "L’app companion aveva una grafica piatta e poco coerente tra dispositivi.",
                "Tema glass adattivo telefono/tablet; in associazione puoi digitare il codice o inquadrare il QR generato da Ecosistema.",
            ),
        ),
    },
    {
        "version": "0.4.58",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Sito e app anche su tablet e telefono",
                "Le novità recenti (Ecosistema a triangolo, bentornato, In ascolto, CTA, APK) erano pensate soprattutto per lo schermo grande.",
                "Ora tablet e telefono hanno layout dedicati: Ecosistema si adatta, tasti a tutta larghezza, safe-area, In ascolto e bentornato centrati; l’APK ripete lo stesso schema su schermi stretti e larghi.",
            ),
        ),
    },
    {
        "version": "0.4.57",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Bentornato più caldo e requisiti password di nuovo verdi",
                "Il messaggio di bentornato stava a sinistra in un rettangolo scuro e i requisiti password (ok) erano diventati blu.",
                "Ora «Che bello rivederti…» è centrato senza riquadro; i requisiti soddisfatti e lo stato «password forte» tornano verdi.",
            ),
        ),
    },
    {
        "version": "0.4.56",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Chiamate APK → In ascolto sul PC, una sola app",
                "Lo squillo dall’APK non compariva su In ascolto (nessun aggiornamento live) e restavano CTA anche dopo i passi già fatti; APK e /app nel browser confondevano.",
                "In ascolto si aggiorna da sola ogni 1,5s e salva lo stato chiamata; Ecosistema nasconde i tasti «da fare» se già fatto; su Android conta solo l’APK (/app/android), il browser non sostituisce il rilevamento.",
            ),
        ),
    },
    {
        "version": "0.4.55",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Ecosistema a triangolo + app Android allineata",
                "Le tre fasi erano in colonna stretta e l’app companion non mostrava lo stesso hub del sito.",
                "In Ecosistema le fasi 1 e 2 stanno affiancate e la 3 (Canali) è centrata sotto; l’app Android ripete lo stesso schema, colori blu vivi e stato cuffia/telefono/Spotify dal heartbeat.",
            ),
        ),
    },
    {
        "version": "0.4.54",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Blu più acceso",
                "Il blu precedente era corretto ma ancora troppo soft sullo schermo.",
                "Accento più luminoso (#00b7ff chiaro, #6ef0ff scuro), CTA e alone più brillanti, sfondo 3D più saturo.",
            ),
        ),
    },
    {
        "version": "0.4.53",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Continua e chat: niente più nero",
                "Il bottone grande «Continua», il fab chat e l’header della chat AI restavano neri anche con l’accento blu: sembrava ancora spento.",
                "Ora quei pezzi usano lo stesso blu vivo dei bottoni primari, con alone — il contrasto nero è tolto dalle CTA principali.",
            ),
        ),
    },
    {
        "version": "0.4.52",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Bottoni e atmosfera finalmente blu",
                "L’accento era blu ma i bottoni primari restavano neri e lo sfondo 3D aveva ancora riflessi verdi: il sito sembrava spento.",
                "Ora Continua/Salva/CTA usano blu vivo con alone, «Iris» in header è colorato, lo sfondo 3D è tutto azzurro — non più nero/verde soft.",
            ),
        ),
    },
    {
        "version": "0.4.51",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Blu elettrico, più saturo",
                "Anche il blu vivace precedente restava un po’ spento sullo schermo.",
                "Accento elettrico #0066ff (chiaro) e #5ad0ff (scuro), con alone più forte: link e bottoni devono saltare subito all’occhio.",
            ),
        ),
    },
    {
        "version": "0.4.50",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Cache /app non blocca più i colori nuovi",
                "Dopo il deploy il blu nuovo c’era sul server, ma browser o PWA potevano tenere CSS vecchi in cache.",
                "Il service worker di /app ora prende CSS/JS dalla rete per primi e svuota le cache vecchie; sul sito normale basta un aggiornamento forzato (Ctrl+F5).",
            ),
        ),
    },
    {
        "version": "0.4.49",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Blu più vivace",
                "L’azzurro precedente risultava spento e il sito sembrava «morto».",
                "Accento più saturo e luminoso (#1e8fff al chiaro, #6bc4ff al scuro): bottoni, link e stati tornano vivi senza riprendere il verde.",
            ),
        ),
    },
    {
        "version": "0.4.48",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Accento azzurro leggero (niente più verde)",
                "Su nero e sul resto del sito l’accento era un verde/salvia: stancava e non era la palette che volevi.",
                "Ora tutto ciò che era verde (bottoni, link, icone, stati ok, bolle chat, /app) usa un azzurro leggero, chiaro e scuro.",
            ),
        ),
    },
    {
        "version": "0.4.47",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Tendina con foto e icone animate",
                "Il menu account era solo testo: niente foto profilo e niente segnali visivi sulle voci.",
                "Accanto a «I miei dati» compare la foto profilo; ogni voce ha un’icona minimale (freccia di uscita su Esci) con animazione al passaggio e al click.",
            ),
        ),
    },
    {
        "version": "0.4.46",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Menu minimale e Ecosistema a step",
                "La tendina a destra aveva troppe voci (cuffia, telefono, password, chatta…): difficile capire dove andare.",
                "Ora solo: I miei dati, Ecosistema, Le mie chat, Esci. Password in I miei dati; dopo l’anagrafica si apre Ecosistema con cuffia → telefono/app → canali (Spotify, Alexa e Google in arrivo).",
            ),
        ),
    },
    {
        "version": "0.4.45",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Ban: fuori subito, non al prossimo login",
                "Se un account veniva sospeso mentre era già dentro, restava in sessione fino a logout/login.",
                "Ora il ban chiude la sessione al primo click o heartbeat: web, /app e companion tornano al login con messaggio di sospensione; anche il token dispositivo viene invalidato.",
            ),
        ),
    },
    {
        "version": "0.4.44",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Collegamento telefono vero (credenziale)",
                "«Associa telefono» era confuso: tanti modi, poco chiaro se fosse un collegamento reale.",
                "Ora /telefono-setup spiega un solo modello: PIN + app (o un tocco sul cellulare) crea una credenziale dispositivo. Scheda chiara: nome, in linea, cosa è reale (chiamate / Spotify).",
            ),
            (
                "Pagine telefono più chiare",
                "Setup e app mescolavano browser, QR, Apple e Spotify senza gerarchia.",
                "Flusso ripulito: collega dispositivo → stato fidato → Spotify opzionale; /app chiede PIN e nome dispositivo.",
            ),
        ),
    },
    {
        "version": "0.4.43",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Colori soft e testo leggibile",
                "Su /app il verde era troppo acceso e i titoli sembravano schiacciati (font stretto + letter-spacing negativo).",
                "Palette più soft (salvia su antracite), solo Outfit con interlinea normale, niente gradiente sulle frasi; autofill del browser non sbianca più i campi.",
            ),
        ),
    },
    {
        "version": "0.4.42",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "App /app in liquid glass",
                "L’app companion era funzionale ma piatta: tipografia generica e poca dinamica.",
                "Ora /app ha vetro liquido (blur, riflessi, orb), font Syne + Outfit e parole che entrano e scivolano con un gradiente vivo.",
            ),
        ),
    },
    {
        "version": "0.4.41",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Percorso Apple Developer → TestFlight",
                "Per l’idea al 100% (app nativa, CallKit, App Store) serviva una guida chiara su cosa fare tu e cosa è già pronto nel codice.",
                "Ora /app/apple e docs/APPLE_DEVELOPER.md spiegano iscrizione (~99 USD/anno), Team ID, App Store Connect e Codemagic; il bridge CXCallObserver è preparato in mobile/ios.",
            ),
            (
                "Due modi sull’iPhone",
                "Non era chiaro cosa usare subito e cosa dopo Apple.",
                "Subito: /app → Aggiungi a Home. Al 100%: dopo la tua iscrizione Developer, TestFlight con com.irisnous.mobile.",
            ),
        ),
    },
    {
        "version": "0.4.40",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "App Iris installabile sull’iPhone",
                "Senza Mac e App Store non c’era un modo chiaro per avere Iris come icona sul telefono.",
                "Ora apri /app in Safari → Condividi → Aggiungi a Home: compare l’icona Iris, a schermo intero. Associa con username, password e codice a 6 cifre; guida su /app/installa.",
            ),
            (
                "Stato e eventi dall’app",
                "L’anteprima HTML non parlava col server.",
                "L’app su /app si collega alle API companion: heartbeat, segnala chiamata, prossima canzone Spotify, come l’app nativa in arrivo.",
            ),
        ),
    },
    {
        "version": "0.4.39",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "App companion Android e iPhone",
                "Per usare il telefono con Iris serviva il browser o scorciatoie; non c’era un’app unica da configurare.",
                "Ora c’è il progetto Flutter in mobile/: una sola app per Android e iPhone (associa, permessi, stato). Su /telefono-setup trovi il riferimento; TestFlight/Play arriveranno dopo.",
            ),
            (
                "Chiamate rilevate dall’app → In ascolto",
                "Il focus chiamata su Iris si aggiornava solo con simulazioni dal sito.",
                "Nuove API companion ricevono call_incoming / call_ended (e musica) dal telefono associato e aggiornano il contesto sempre in ascolto — senza fingere di rispondere o rifiutare la chiamata cellulare.",
            ),
        ),
    },
    {
        "version": "0.4.38",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Telefono: associa, Spotify, ponte chiamate",
                "Associazione e Spotify c’erano, ma il percorso non era chiaro e le chiamate non arrivavano bene su Telefono live.",
                "Ora /telefono-setup ha due passi chiari (associa → Spotify), un tocco «Associa questo dispositivo», e Telefono live mostra le chiamate del ponte; Spotify resta reale quando è collegato.",
            ),
            (
                "Onesti su cosa è reale",
                "Si rischiava di sembrare che Iris controllasse la tipica chiamata cellulare o Alexa.",
                "Chiaro in UI: chiamate = ponte browser + SÌ/NO; musica = Spotify Premium vero; niente Alexa inventata.",
            ),
        ),
    },
    {
        "version": "0.4.37",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "In ascolto, senza accendere nulla",
                "C’era una «modalità live» e un «router» da attivare a mano: sembrava un’opzione tecnica, non il comportamento normale.",
                "Ora Iris è sempre in ascolto dopo il login: SÌ/NO si applica a ciò che sta succedendo (chiamata > messaggio > musica). La pagina «In ascolto» spiega solo cosa succede, senza gergo.",
            ),
            (
                "Pensa SÌ/NO vicino alla calibrazione",
                "Premendo SÌ o NO dopo un evento, a volte Iris riconosceva il contrario: prendeva una finestra EEG poco legata al pensiero e la classificazione sembrava a caso.",
                "Ora ogni Pensa SÌ/NO crea un impulso nuovo vicino ai modelli della calibrazione (con una piccola variazione), poi confronta per similarità: di solito resta allineato al tasto, senza essere una copia identica.",
            ),
        ),
    },
    {
        "version": "0.4.36",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "SÌ/NO per similarità, non replay",
                "Il modello ripeteva l’impulso identico della calibrazione: poco realistico, perché l’attività cerebrale non è mai uguale.",
                "Ora ogni Pensa SÌ/NO acquisisce una nuova finestra EEG e la classifica per similarità ai modelli SÌ/NO della calibrazione; /contesto mostra «riconosciuto come» e i punteggi.",
            ),
        ),
    },
    {
        "version": "0.4.35",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "SÌ/NO come in calibrazione",
                "Su /contesto i tasti Pensa SÌ/NO acquistavano una nuova finestra EEG ogni volta: stessa famiglia, non l’impulso salvato in cuffia.",
                "Ora la cuffia virtuale ripete l’impulso SÌ/NO della calibrazione (stesse feature); se manca il modello, acquisisce ancora una finestra nuova.",
            ),
        ),
    },
    {
        "version": "0.4.34",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Testi cuffia di nuovo leggibili",
                "Nella calibrazione SÌ/NO, col tema scuro, testo e pulsante «Pensa NO» sparivano sulla scheda chiara: sembrava una pagina vuota.",
                "Ora scheda e pulsanti hanno contrasto corretto in chiaro e scuro: istruzioni, conteggi e «Pensa NO» si leggono bene.",
            ),
        ),
    },
    {
        "version": "0.4.33",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Router contesto SÌ/NO",
                "La cuffia sapeva solo etichette semplici, ma non c’era un posto chiaro dove il sito dicesse a cosa si applica il SÌ/NO quando coincidono chiamata, messaggio e musica.",
                "Ora /contesto mostra il focus attivo («Sto decidendo su…»), simula eventi e instrada SÌ/NO con priorità chiamata > messaggio > musica; Spotify e ponte telefono dove già esistono.",
            ),
        ),
    },
    {
        "version": "0.4.32",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Hub «Il tuo telefono»",
                "Associazione telefono, Spotify e Telefono live erano sparsi, senza un percorso chiaro dal browser dello smartphone.",
                "Ora /telefono-setup ha due tappe: perché + codice/QR, poi stato, Spotify e Alexa «dopo»; funziona anche solo dal telefono.",
            ),
        ),
    },
    {
        "version": "0.4.31",
        "intro": WHATS_NEW_INTRO,
        "entries": (
            (
                "Hub «La tua cuffia»",
                "Associazione e calibrazione erano mescolate con codice email e telefono, senza un percorso chiaro SÌ/NO dal telefono.",
                "Ora /cuffia ha due tappe: associazione (accendi, indossa, contatto) e calibrazione pensa SÌ / pensa NO; telefono resta separato (prossimamente).",
            ),
        ),
    },
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
