# Iris Nous — APK Android (prova senza Play Store)

L’app Flutter in `mobile/` è **unica per Android e iPhone**. Su Android puoi provarla subito con un file **APK**, senza pagare Google.

## Installazione sul telefono

1. Copia `mobile/build/app/outputs/flutter-apk/app-release.apk` (o `app-debug.apk`) sul telefono (USB, Drive, WhatsApp a te stessa…).
2. Apri il file → se chiede, abilita **Installa app sconosciute** per quella app (Chrome/File).
3. Apri **Iris Nous** → Accedi con username, password e codice a 6 cifre da [Il tuo telefono](https://iris-nous.onrender.com/telefono-setup).
4. In **Permessi** concedi **Stato telefono** (e notifiche se vuoi).
5. Prova: una chiamata in arrivo dovrebbe aggiornare Iris (*In ascolto*); oppure usa «Simula squillo».

## Build in locale (Windows)

Prerequisiti: Flutter (`C:\src\flutter`), Android Studio (SDK), licenze accettate.

```powershell
$env:Path = "C:\src\flutter\bin;" + $env:Path
cd mobile
flutter create . --project-name iris_nous_mobile --org com.irisnous --platforms=android,ios
flutter pub get
flutter build apk --release
```

APK: `mobile/build/app/outputs/flutter-apk/app-release.apk`

## Cosa funziona (Android)

| Funzione | Stato |
|----------|--------|
| Associazione Iris (codice) | Sì |
| Heartbeat / stato | Sì |
| Rilevamento chiamata (`TelephonyCallback`) | Sì (con permesso) |
| Prossima canzone Spotify | Sì (se collegato sul sito) |
| Rispondi/rifiuta cellulare OS | No (limite onesto) |

iPhone: stesso codice; installazione stabile richiede Apple Developer (vedi `APPLE_DEVELOPER.md`). Intanto su iPhone usa `/app`.
