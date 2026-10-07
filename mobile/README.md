# Iris Nous — app companion (Flutter)

Una sola app per **Android e iPhone**: configura l’associazione con Iris, gestisce i **permessi** in modo chiaro, e (nella fase successiva) rileva le chiamate per aggiornare *In ascolto* — **senza Shortcuts**.

> **Onestà:** l’app **non** può rispondere o rifiutare la tipica chiamata cellulare del sistema operativo. SÌ/NO dalla cuffia possono aggiornare Iris e, al massimo, aprire la UI Telefono / dare indicazioni in-app. SMS/iMessage **non** vengono letti in questa versione.

## Perché Flutter (un solo codice)

| Motivo | Dettaglio |
|--------|-----------|
| Un UI | Stesse schermate IT su Android e iPhone |
| Permessi | Plugin `permission_handler` + manifest/Info.plist espliciti |
| Nativo dopo | Platform channel per `TelephonyCallback` (Android) e `CXCallObserver` (iOS) |
| Manutenzione tesi | Un repo, un README, niente doppia app Swift/Kotlin |

Non c’è uno scaffold Swift-only: la cartella primaria è `mobile/`.

## Aprire e avviare

### Prerequisiti

1. [Flutter](https://docs.flutter.dev/get-started/install) stabile (3.22+)
2. Android Studio **oppure** Xcode 15+ (Mac) per iPhone
3. Account Iris sul sito (`https://iris-nous.onrender.com`) e codice a 6 cifre da **Il tuo telefono**

### Prima volta (consigliato)

Su questa macchina di sviluppo Flutter non era installato: la struttura è già scritta a mano. Dopo aver installato Flutter:

```bash
cd mobile
flutter create . --project-name iris_nous_mobile --org com.irisnous --platforms=android,ios
```

`flutter create .` completa i file di piattaforma mancanti **senza cancellare** `lib/` se rispondi in modo da preservare i file esistenti. Poi:

```bash
flutter pub get
flutter run
```

- **Android:** telefono USB con debug, o emulatore → `flutter run -d android`
- **iPhone:** Mac + cavo / simulatore → `flutter run -d ios` (poi Xcode → Signing con il tuo Team). Bundle id suggerito: `com.irisnous.mobile`

URL predefinito API: `https://iris-nous.onrender.com` (modificabile in Accedi).

### Schermate (MVP)

1. **Splash** → se già associato va a Stato  
2. **Accedi / Associa** — username, password, codice 6 cifre  
3. **Stato** — chiamata / musica / focus Iris, heartbeat, link a In ascolto / cuffia in browser  
4. **Permessi** — elenco con spiegazione e tasto «Richiedi» (uno alla volta)

## Tabella permessi (Italiano)

Richiesta **graduale** in app (schermata Permessi), non tutti al primo avvio.

### Android

| Permesso | Manifest | Perché (testo utente) | Note moderne |
|----------|----------|------------------------|--------------|
| Internet | `INTERNET` | Collegarsi al tuo account Iris | Sempre necessario |
| Stato telefono | `READ_PHONE_STATE` | *Per capire se arriva una chiamata e aggiornare Iris, senza rispondere al posto tuo.* | API 31+: preferire `TelephonyCallback.CallStateListener`. Non consente answer/reject. |
| Numeri telefono | `READ_PHONE_NUMBERS` | Opzionale: leggere i numeri associati al dispositivo | API 26+; chiedere solo se serve |
| Log chiamate | `READ_CALL_LOG` (**non attivo** nel manifest MVP) | Solo se in futuro serve il nome/numero chiamante da log | Android 10+: permesso pericoloso; Play policy stretta |
| Notifiche | `POST_NOTIFICATIONS` | *Per avvisarti quando Iris riceve un evento* | Android 13+ (API 33) |
| Servizio in primo piano | `FOREGROUND_SERVICE` (+ `SPECIAL_USE`) | Heartbeat / osservazione chiamate con schermo spento | Dichiarato; servizio da implementare |
| Batteria | `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS` | Evitare che il sistema uccida il heartbeat | Richiedere solo se l’utente attiva il background |
| SMS | — | **Non richiesto** | Niente `READ_SMS` finché i messaggi non esistono |

### iOS

| Capacità / chiave | Perché (testo utente) | Note |
|-------------------|------------------------|------|
| `CXCallObserver` (CallKit) | *Per capire se arriva una chiamata (squillo / fine) e aggiornare Iris.* | Osservazione ok con app in esecuzione; **non** answer/reject cellulare |
| `UIBackgroundModes`: `fetch`, `processing` | Heartbeat periodico verso Iris | Non garantisce sempre-on; Fase FGS/BGTask |
| `NSUserNotificationsUsageDescription` | Notifiche eventi Iris | Testo EN+IT in Info.plist |
| Microfono | — | **Non** dichiarato (evitato) |
| App Tracking (`NSUserTracking…`) | — | **Non** usato |
| SMS / iMessage | — | **Non leggibili** dalle app terze |

Bundle id: `com.irisnous.mobile`.  

**Apple / TestFlight:** guida completa in [`docs/APPLE_DEVELOPER.md`](../docs/APPLE_DEVELOPER.md) e sul sito `/app/apple`. Serve la tua iscrizione al Apple Developer Program (~99 USD/anno); poi Mac+Xcode oppure Codemagic (`codemagic.yaml`).

## API Iris usate dall’app

| Metodo | Path | Auth |
|--------|------|------|
| POST | `/api/companion/pair` | username + password + `code` → `device_token` |
| POST | `/api/companion/heartbeat` | `Authorization: Bearer <token>` |
| GET | `/api/companion/status` | Bearer o sessione |
| POST | `/api/companion/event` | Bearer — `call_incoming`, `call_ended`, `music_playing`, `music_stopped` |
| POST | `/api/companion/music/next` | Bearer — Spotify via backend Iris |

## Prossimi passi (call observer)

1. **Android:** `TelephonyCallback` / `PhoneStateListener` → `POST /api/companion/event` (`call_incoming` / `call_ended`)  
2. **iOS:** `CXCallObserver` via platform channel Dart ↔ Swift  
3. Foreground service / BGTask per heartbeat con schermo spento  
4. Rimuovere i tasti «Simula squillo» quando il rilevamento nativo è stabile  
5. Dopo iscrizione Apple: TestFlight (vedi `docs/APPLE_DEVELOPER.md`) — CXCallObserver già in `ios/Runner/CallObserverBridge.swift`

## Limiti (da ripetere all’utente)

- **No** risposta/rifiuto programmatico della chiamata cellulare tipica  
- **No** lettura SMS/iMessage in questa versione  
- Musica = OAuth Spotify già sul sito Iris; l’app usa le API companion  
- SÌ/NO cuffia resta sul web (*In ascolto*) o arriverà dopo
