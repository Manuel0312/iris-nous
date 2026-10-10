# Apple Developer → TestFlight → App Store (Iris Nous)

Percorso per avere Iris **come app nativa al 100%** sull’iPhone (CallKit, notifiche, TestFlight, App Store).

> **Cosa può fare solo tu:** iscriverti e pagare l’Apple Developer Program con il tuo Apple Account e i tuoi documenti.  
> **Cosa è già pronto nel repo:** codice Flutter, API companion, PWA `/app`, bridge CallKit (bozza), metadata App Store, pipeline Codemagic / GitHub Actions IPA.

---

## Percorso gratis (Windows, senza €99): app nativa + Sideloadly

Per **prova dimostrativa sul tuo iPhone** (permessi, chiamate, non PWA) **non** serve il Program a pagamento e **non** serve un Mac a casa.

1. Su GitHub → Actions → **iOS IPA (Sideloadly)** → **Run workflow** (workflow: `.github/workflows/ios-ipa-sideload.yml`).
2. A fine build scarica l’artifact `iris-nous-ios-ipa-unsigned` → file `IrisNous-unsigned.ipa`.
3. Sul PC Windows: installa **iTunes + iCloud** dal sito Apple (non dallo Store), poi **Sideloadly**.
4. Collega l’iPhone (sblocca, “Considera attendibile”), apri Sideloadly, metti il tuo **Apple ID** gratis, trascina l’`.ipa` → **Start**.
5. Su iPhone: Impostazioni → Generali → VPN e gestione dispositivo → autorizza il tuo Apple ID.
6. Apri **Iris Nous** (icona vera, non Safari): concedi i permessi e fai la prova chiamata.

**Limiti free Apple:** la firma scade ~**7 giorni**; ricolleghi il telefono e ripeti Start su Sideloadly (i dati restano). Non è App Store / TestFlight: va bene per tesi/demo personale.

Quando vorrai stabilità senza rinnovi settimanali: iscrizione Developer (~99 €/anno) → sezione sotto → TestFlight.

---

## Perché serve l’account a pagamento

| Cosa vuoi | Serve |
|-----------|--------|
| Icona in Home subito (PWA) | No — già su https://iris-nous.onrender.com/app |
| App nativa sul *tuo* iPhone per prova (7 giorni) | Apple ID gratis + IPA (Actions) + Sideloadly — vedi sopra |
| **TestFlight** (link di installazione stabile) | **Apple Developer Program (~99 USD/anno)** |
| **App Store** pubblico | Stesso Program + review Apple |
| Rilevare chiamate in demo personale | App nativa firmata (anche free/Sideloadly); la PWA non basta |

Senza Program **non** si può pubblicare né dare un IPA “ufficiale” ad altri tester; per **te stessa** sul tuo telefono il percorso Sideloadly è sufficiente.

---

## Passo 1 — Tu: iscrizione (30–60 min + verifica)

1. Sul **tuo iPhone** installa l’app [**Apple Developer**](https://apps.apple.com/app/apple-developer/id640199958) **oppure** apri dal computer:  
   https://developer.apple.com/programs/enroll/
2. Accedi con un **Apple Account** che abbia:
   - autenticazione a **due fattori** attiva  
   - **nome e cognome legali** (non nickname: altrimenti ritardi)
3. Scegli iscrizione come **Individuale** (persona fisica) — per la tesi va bene.
4. Verifica i dati (indirizzo reale, non casella postale; telefono).
5. Accetta il **Apple Developer Program License Agreement**.
6. **Paga** la quota annuale (in Italia di solito ~99 USD / ~99 € IVA inclusa, come mostrato al checkout).
7. Attendi l’email di conferma. A volte Apple chiede un documento d’identità: rispondi subito.

Quando è attivo, su https://developer.apple.com/account vedi **Membership** con data di scadenza e **Team ID**.

**Scrivimi (o annota qui) il Team ID** — serve per firmare l’app `com.irisnous.mobile`.

---

## Passo 2 — Tu: App Store Connect (dopo Membership)

1. Vai su https://appstoreconnect.apple.com  
2. Accetta i contratti se richiesti.  
3. **My Apps → + → New App**  
   - Platform: iOS  
   - Name: `Iris Nous`  
   - Primary language: Italian  
   - Bundle ID: crea prima su https://developer.apple.com/account/resources/identifiers/list  
     - App ID: `com.irisnous.mobile`  
     - Capabilities: Push Notifications (quando serve), Background Modes già in Info.plist  
   - SKU: `iris-nous-mobile` (interno, a tua scelta)  
   - User Access: Full Access  

4. Compila bozza scheda (testi già in `mobile/metadata/app_store_it.md`).

---

## Passo 3 — Mac o cloud (build IPA)

Su questo PC Windows **non** si firma un’app iOS. Serve uno di questi:

### Opzione A — Mac (Xcode) [classica]

1. Installa **Xcode** (App Store Mac) + **Flutter**.  
2. Nel repo:

```bash
cd mobile
flutter create . --project-name iris_nous_mobile --org com.irisnous --platforms=android,ios
# conserva i file già presenti in lib/ e ios/Runner quando chiede
flutter pub get
cd ios && pod install && cd ..
open ios/Runner.xcworkspace
```

3. In Xcode: **Signing & Capabilities** → Team = il tuo Team Apple Developer.  
4. Collega l’iPhone → Run, oppure **Product → Archive** → Distribute → **TestFlight**.

### Opzione B — Codemagic (Mac in cloud, senza comprare Mac)

1. Account su https://codemagic.io (login GitHub sul repo `iris-nous`).  
2. Collega il repo; usa `codemagic.yaml` già in root.  
3. In Codemagic → **Code signing identities** carica:
   - certificato iOS Distribution (`.p12`)  
   - provisioning profile App Store / Ad Hoc  
   (si generano da Apple Developer → Certificates, Identifiers & Profiles)  
4. Avvia la build → scarica IPA o pubblica su TestFlight con API key App Store Connect.

Guida certificati: https://docs.codemagic.io/flutter-code-signing/ios-code-signing/

---

## Passo 4 — TestFlight sull’iPhone

1. In App Store Connect → Iris Nous → **TestFlight**.  
2. Carica il build (Xcode Organizer o Codemagic).  
3. Compila **Export Compliance** (Iris non usa crittografia custom oltre HTTPS → di solito “No” a encryption proprietary).  
4. Aggiungi te stessa come **Internal Tester**.  
5. Sul iPhone: app **TestFlight** → accetta l’invito → **Installa Iris Nous**.

Da quel momento l’app è “vera” al 100% sul tuo telefono (firma Apple, aggiornamenti OTA).

---

## Cosa implementiamo nel codice (stato)

| Pezzo | Stato |
|-------|--------|
| API companion (pair, heartbeat, eventi) | Fatto (sito) |
| UI Flutter Accedi / Stato / Permessi | Fatto (`mobile/lib`) |
| PWA installabile `/app` | Fatto (ponte finché non c’è TestFlight) |
| Bundle id `com.irisnous.mobile` | Fatto |
| Info.plist + background + notifiche | Fatto |
| Privacy Manifest `PrivacyInfo.xcprivacy` | Preparato |
| `CXCallObserver` → eventi Iris | Bridge Swift/Dart preparato |
| Progetto Xcode completo (`.xcodeproj`) | Si completa con `flutter create` su Mac/CI |
| Firma / TestFlight | **Dopo la tua iscrizione** |

---

## Checklist rapida (tu)

- [ ] Apple Account con 2FA e nome legale  
- [ ] Iscrizione Apple Developer Program pagata  
- [ ] Team ID annotato  
- [ ] Identifier `com.irisnous.mobile` creato  
- [ ] App creata in App Store Connect  
- [ ] Mac **oppure** Codemagic con certificati  
- [ ] Primo build su TestFlight  
- [ ] Installazione su iPhone 16 e prova associazione Iris  

Quando hai fatto i primi tre punti, dimmelo: con Team ID e accesso (o Codemagic) si completa firma e primo TestFlight.

---

## Link ufficiali

- Iscrizione: https://developer.apple.com/programs/enroll/  
- Aiuto IT: https://developer.apple.com/it/help/account/membership/program-enrollment/  
- App Store Connect: https://appstoreconnect.apple.com  
- Account Developer: https://developer.apple.com/account  
