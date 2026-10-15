# Persistenza su Render (tesi)

## Problema
Sul piano **free** di Render il filesystem sotto `/data` è **effimero**: sleep (~15 min) e redeploy possono cancellare `accessi.db`, `photos/` e `headsets/`.

## Cosa fa Iris oggi
1. **SQLite** in `/data/accessi.db` (account, anagrafica, context_world).
2. **Backup cifrato su GitHub** (branch `iris-data`) se `BCI_IOT_DATA_BACKUP=1` + token:
   - include `accessi.db`, `photos/`, **`headsets/`** (calibrazione)
   - **debounced** (~8s): non fa commit a ogni riga (evita lock/corruzione).
3. Restore automatico al boot se il disco è vuoto.

## Ponte PC ↔ cloud (split-brain)
Il worker locale **non** è lo stesso processo di Render.

```bash
# 1) Associa il telefono / genera token companion sul sito
# 2) Esporta:
set BCI_IOT_PUBLIC_URL=https://iris-nous.onrender.com
set BCI_IOT_WORKER_TOKEN=<token da companion pair>

# 3) Pipeline locale → push SÌ/NO al cloud
bci-iot run --windows 20 --cloud --profile-latency
```

API: `POST /api/companion/intent` (Bearer token) — **senza** impulso cuffia cloud; il PC ha già classificato.

## Migrazione consigliata (dopo la tesi / se serve stabilità)

### Database
- Crea un Postgres free (**Neon**, **Supabase** o addon Render 90 giorni).
- Imposta `DATABASE_URL=postgresql://…` (oggi Iris resta su SQLite; la migrazione completa è un passo successivo: refactor `AccessDatabase`).
- Finché resti su SQLite: **non spegnere** il backup GitHub.

### Foto
- Opzione A: resta `photos/` nel bundle backup (ok tesi).
- Opzione B: Cloudinary / S3 free + URL in profilo (da implementare quando serve).

## Checklist demo commissione
- [ ] Manual Deploy dopo l’ultimo push
- [ ] `GET /health` mostra la versione attesa
- [ ] Backup env attivi su Render
- [ ] Prova account + foto dopo uno sleep di 20 minuti
