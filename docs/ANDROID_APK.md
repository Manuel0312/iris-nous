# Iris Nous — APK Android (prova senza Play Store)

L’app Flutter in `mobile/` è **unica per Android e iPhone**. Su Android puoi provarla subito con un file **APK**, senza pagare Google.

## Installazione sul telefono

Path canonico (sempre **sovrascritto**, mai versioni parallele): `IrisNous-apk/IrisNous.apk`.

1. Dopo Actions **Android APK**: `.\scripts\fetch-mobile-builds.ps1 -ApkOnly` (oppure, in locale dopo `flutter build apk --release`, copia `mobile/build/app/outputs/flutter-apk/app-release.apk` → `IrisNous-apk/IrisNous.apk` con `-Force`). Lo script aggiorna anche `src/bci_iot/web/static/mobile/build-manifest.json` (SHA-256).
2. Copia `IrisNous-apk/IrisNous.apk` sul telefono (USB, Drive, WhatsApp…).
3. **Verifica anti-manomissione:** apri [ /app/android ](https://iris-nous.onrender.com/app/android), scegli l’APK e controlla che lo SHA-256 combaci (manifesto: `/api/mobile/integrity`). Hash diverso → non installare.
4. Apri il file → se chiede, abilita **Installa app sconosciute** per quella app (Chrome/File). Play Protect può avvisare: fuori dallo store è normale per un APK di tesi firmato in sideload.
5. Apri **Iris Nous** → Accedi con username, password e codice a 6 cifre da [Il tuo telefono](https://iris-nous.onrender.com/telefono-setup).
6. In **Permessi** concedi **Stato telefono** (e notifiche se vuoi).
7. Prova: una chiamata in arrivo dovrebbe aggiornare Iris (*In ascolto*); oppure usa «Simula squillo».

## Build in locale (Windows)

Prerequisiti: Flutter (`C:\src\flutter`), Android Studio (SDK), licenze accettate.

```powershell
$env:Path = "C:\src\flutter\bin;" + $env:Path
cd mobile
flutter create . --project-name iris_nous_mobile --org com.irisnous --platforms=android,ios
flutter pub get
flutter build apk --release
Copy-Item .\build\app\outputs\flutter-apk\app-release.apk ..\IrisNous-apk\IrisNous.apk -Force
```

APK canonico: `IrisNous-apk/IrisNous.apk`

## Cosa funziona (Android)

| Funzione | Stato |
|----------|--------|
| Associazione Iris (codice) | Sì |
| Heartbeat / stato | Sì |
| Rilevamento chiamata (`TelephonyCallback`) | Sì (con permesso) |
| Prossima canzone Spotify | Sì (se collegato sul sito) |
| Anteprima messaggi (WhatsApp…) | Sì con «Accesso alle notifiche»; SÌ mostra testo e apre l’app |
| Rispondi/rifiuta cellulare OS | Parziale (Telecom / limiti OEM) |

iPhone: stesso codice; installazione stabile richiede Apple Developer (vedi `APPLE_DEVELOPER.md`). Intanto su iPhone usa `/app`.
