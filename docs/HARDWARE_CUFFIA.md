# Guida unificata — Cuffia Iris (PDF + repo)

Documento operativo per Cursor e per la tesi: **mescola** la visione della
`Guida_Sviluppo_Cuffia_Neurale.pdf` con ciò che Iris Nous ha **già** nel repo.
Non ripartire da zero (né Flutter, né ADC fai-da-te).

## 1. Cosa tenere dal PDF (buono)

| Idea PDF | Perché resta |
|----------|----------------|
| Azioni di sistema **non** nell’app sandbox | iOS/Android bloccano chiamate/notifiche dal WebView |
| Protocollo tipo **HFP / HID / bridge nativo** | Il telefono tratta Iris come “dispositivo fidato” |
| Lab su PC prima dell’edge | Dataset, filtri, modello, proof of concept |
| App = calibrazione + stato, non telecomando continuo | Allinea a `PRODUCT_UX.md` |
| Fake call / test VoIP prima della SIM | CallKit / ConnectionService già citati nel codice |

## 2. Cosa scartare dal PDF (per Iris)

| Idea PDF | Alternativa Iris |
|----------|------------------|
| EEG grezzo + ESP32 da soli | **OpenBCI Cyton 8 ch** + BrainFlow |
| Edge AI obbligatoria subito sul MCU | Classificazione su **server / PC** finché non c’è segnale reale stabile |
| App nuova in Flutter/RN | **App attuale** (`/app`, shell, APK/IPA) |
| Accuracy >85% come requisito | Target tesi: pipeline + demo onesta, metriche misurate |
| 5 prompt “da zero” | Estendere `acquisition/`, `headset_agent`, bridge nativo |

## 3. Architettura ibrida (la “cosa migliore”)

```text
┌─────────────────────────────┐
│  Cuffia (sim o OpenBCI)     │  potenza / wear / contact / EEG
└──────────────┬──────────────┘
               │ BLE/serial (BrainFlow)  oggi: simulato in agent
               ▼
┌─────────────────────────────┐
│  Iris server + HeadsetAgent │  features → ML → contesto SÌ/NO
│  (già nel repo)             │
└──────────────┬──────────────┘
               │ intent (SÌ/NO + contesto)
               ▼
┌─────────────────────────────┐
│  Bridge telefono (nativo)   │  APK/IPA: permessi, CallKit,
│  ← idea HFP/HID del PDF     │  notifiche, Spotify session
└─────────────────────────────┘
               │
               ▼
     chiamate / messaggi / musica / (poi casa)
```

- **Cervello / modello:** resta nel mondo Iris (Python, priors, calibrazione), non TFLM su ESP32 al giorno 1.
- **Muscoli sul telefono:** bridge nativo (e, più avanti, eventuale profilo BT “hands-free” se serve indipendenza totale dall’app aperta).
- **App companion:** già esiste — account → associa BT simulato → calibra → permessi → Spotify.

## 4. Mappa PDF → file già presenti

| Fase PDF | Dove sta già / dove va |
|----------|-------------------------|
| Setup Python / venv | Repo + `.venv` |
| Acquisizione | `src/bci_iot/acquisition/` (`synthetic`, `brainflow_source`) |
| Filtri / features | pipeline features + `docs/EEG_PRIORS.md` |
| Training / classificazione | `src/bci_iot/ml/`, esperimenti in `docs/EXPERIMENTS.md` |
| Agent cuffia (power/wear/contact) | `src/bci_iot/pipeline/headset_agent.py` |
| UX associazione / calibrazione | shell app: Accendi → Cerca BT → Associa → Indossa → SÌ/NO |
| Contesto chiamate/musica | `context_router`, schermate In ascolto / Musica / Permessi |
| Spotify | OAuth in-app → torna a `/app?...&screen=musica` |
| Fake / bridge chiamate | `nativeBridge`, CallKit notes in `app.py` |
| Hardware reale | OpenBCI + stampa A1 mini — vedi tabella sotto e skill `cuffia-reale` |

## 5. Fasi di lavoro (ordine fisso)

### Fase A — Ora (senza board fisica)
1. Flusso app: account → **Accendi → Bluetooth simulato → Associa Iris → Indossa → calibra**.
2. Permessi + Spotify dall’app.
3. In ascolto: eventi simulati + SÌ/NO.
4. Nessun claim “cuffia fisica collegata” in UI pubblica.

### Fase B — Laboratorio con Cyton (quando arriva) — **codice pronto**
1. `src/bci_iot/acquisition/brainflow_openbci.py` + `factory` `brainflow_cyton` (fallback synthetic).
2. `HeadsetAgent` usa `brainflow_openbci` se `BCI_IOT_BRAINFLOW_BOARD` / `SERIAL_PORT` sono impostati.
3. Script: `scripts/lab_collect_yes_no.py` (SÌ/NO/riposo + notch 50 + bandpass 1–40).
4. Env tipico Windows: `BCI_IOT_BRAINFLOW_BOARD=cyton` e `BCI_IOT_BRAINFLOW_SERIAL_PORT=COM3`.

### Fase C — Bridge telefono — **cablato, limiti OS documentati**
1. Vedi `docs/NATIVE_BRIDGE.md` + APK/IPA `openPermissions` / `ensureCallBridge`.
2. Dove l’OS lo consente: heartbeat + CallKit / telephony.
3. HFP/HID firmware: solo se i permessi app non bastano (non sostituisce OpenBCI).

### Fase D — Edge AI (solo se serve, dopo B)
Conversione modello leggero (TFLM / Edge Impulse) su co-processore: **opzionale**, non bloccante per tesi. Priorità: segnale buono + bridge telefono.

## 6. Hardware (decisioni bloccate)

| Pezzo | Scelta |
|-------|--------|
| Elettronica | OpenBCI **Cyton 8 ch** (Daisy 16 ch più avanti) |
| Scocca | Ultracortex / derivata, stampata **Bambu A1 mini** a quarti |
| Non fare | ADC/ampli da zero, Muse/Emotiv come cuffia Iris principale |
| Canali partenza | Fp1, Fp2, F3, F4, C3, Cz, C4, Pz + ref/bias orecchio |

Dettaglio prezzi/stampante: `.cursor/skills/cuffia-reale/reference.md`.

## 7. Prompt Cursor (adattati a questo repo)

Usare **questo file** + il codice esistente, non la guida PDF grezza.

1. *“Secondo `docs/HARDWARE_CUFFIA.md` fase B: aggiungi source BrainFlow Cyton con fallback synthetic, senza rompere `headset_agent`.”*
2. *“Script lab: raccolta finestre SÌ/NO/riposo via agent/BrainFlow in CSV sotto `data/`, filtri notch+bandpass.”*
3. *“Bridge nativo: elenca gap APK/IPA per chiamate/notifiche rispetto a `nativeBridge` e PRODUCT_UX.”*
4. *“Non creare progetto Flutter; estendi `/app` e shell.”*

## 8. Criteri di “fatto” tesi (onesti)

- [ ] Flusso simulato end-to-end in app (associazione → calibrazione → permessi → Spotify).
- [ ] Con board: stream BrainFlow + QC contatto + almeno una sessione SÌ/NO loggata.
- [ ] Bridge: almeno un’azione telefono dimostrabile su APK o IPA (anche in foreground).
- [ ] Testo tesi: limiti (non device medico; accuratezza misurata, non inventata).

---

**In una frase:** il PDF dà la *strategia OS* (BT/nativo fa le azioni); Iris dà lo *stack* (OpenBCI + agent + app). Insieme: stessa UX, elettronica aperta, niente riscrittura da zero.
