# Visione UX Voilà (bloccata)

## Obiettivo quotidiano

Come il **controllo vocale** (Siri / Alexa), non come un’app da guardare:

> Pensi → l’azione succede. **Niente schermate** sul telefono per verificare
> se il pensiero era giusto. Il telefono può restare in tasca / bloccato.

Esempi:

| Contesto | Pensiero | Effetto |
|----------|----------|---------|
| Squilla una chiamata | “chiudi / rifiuta” | La chiamata si chiude |
| Musica in riproduzione | “spegni / pausa” | La musica si ferma |
| Casa | “luce / spina” | Alexa (o HA) esegue |

Il telefono **non è il telecomando a schermo**. È uno dei *target* dell’azione
(chiamate, media). Casa passa da Alexa / Home Assistant.

## Cosa vede l’utente

1. **Setup (una volta, sito):** account → anagrafica → calibrazione → associazione.
2. **Uso quotidiano:** cuffia indossata; **zero UI di conferma**.
3. **Sito / “app”:** solo impostazioni, calibrazione, stato cuffia — non il flusso
   di ogni comando.

Le demo `/demo` e `/cartelle` restano **laboratorio / tesi** (per vedere cosa
capisce il sistema), non il modello d’uso finale.

## Catena tecnica (quando ci saranno i bridge)

```text
Cuffia EEG
   → classificazione intenzioni (server Voilà)
   → contesto automatico (chiama? musica on? idle?)
   → azione diretta
        ├─ telefono (Telecom / media session)   [bridge OS]
        └─ casa (Alexa / Home Assistant)        [integrazione]
```

Il **contesto** sostituisce la domanda “cosa volevi?”:

- se squilla → gli intenti mappano su rispondi/rifiuta;
- se c’è audio → play/pausa/next;
- altrimenti → comandi casa (luci, prese) via Alexa.

## Perché non chiediamo conferma a schermo

La conferma UI rompe la metafora Siri. La sicurezza si gestisce altrimenti:

- soglia di confidenza alta;
- calibrazione personale;
- (opzionale in futuro) “wake mentale” raro, non un popup a ogni azione.

## Piattaforme (onestà)

- **Android:** bridge background più realistico (servizio + intent / accessibilità).
- **iOS:** più vincoli Apple; spesso si passa da Shortcuts / Home / Alexa cloud.
- **Tesi ora:** sito + pipeline + dry-run; bridge reali **dopo** il sito funzionale.

## Decisione prodotto

| Prima (vecchio copy) | Ora (intento Maria) |
|----------------------|---------------------|
| Canali aperti + SÌ/NO a schermo | Azione diretta in background |
| Telefono come UI di verifica | Telefono come dispositivo comandato |
| Cartelle colorate = uso quotidiano | Cartelle = calibrazione / demo laboratorio |
