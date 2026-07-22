# Voilà — Smart System (ex BCI→IoT) (UNITO — tesi triennale Informatica)

Pipeline software per decodificare EEG (prima simulato, poi cuffia reale),
classificarlo in intenti e instradarli verso azioni digitali (smart home, media).
Include una futura **web app** di configurazione personale (iPhone-friendly),
non commerciale.

## Struttura

```text
src/bci_iot/
  acquisition/     # sorgenti EEG (SyntheticBoard, file, hardware)
  preprocessing/   # filtri, artefatti, feature α/β
  ml/              # classificatore + adaptation
  router/          # FSM intento → azione
  integrations/    # Home Assistant, Spotify, stub chiamate
  accounts/        # profilo utente / registrazione cuffia (web)
  pipeline/        # orchestrazione end-to-end
  web/             # API/config app (fase successiva)
configs/           # YAML di configurazione
tests/             # pytest — eseguire a fine ogni sessione
notebooks/         # analisi sperimentali (non runtime)
models/            # artefatti modello (gitignored i pesi)
data/              # dati locali (gitignored)
```

## Setup rapido

```powershell
cd "$env:USERPROFILE\OneDrive\Desktop\TESI"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
```

## Test (fine sessione)

```powershell
pytest
```

## Train modello ML (sklearn)

```powershell
bci-iot train --out models/baseline.joblib
```

## Esperimenti tesi (baseline MoABB-paradigm)

```powershell
bci-iot experiment --mode surrogate
```

Report in `results/experiments/latest.md`. Dettagli: `docs/EXPERIMENTS.md`.
Opzionale MoABB reale: `pip install -e ".[experiments]"`.

## Pipeline software (CLI)

```powershell
.\.venv\Scripts\Activate.ps1
bci-iot train --out models/baseline.joblib
bci-iot calibrate --user maria
bci-iot run --windows 10 --context music_mode --model models/baseline.joblib
bci-iot run --windows 5 --source brainflow_synthetic --context music_mode
```

Sorgenti EEG:
- `synthetic` — NumPy (default)
- `brainflow_synthetic` — BrainFlow SyntheticBoard (`pip install -e ".[acquisition]"`)

`dry_run: true` in `configs/default.yaml` → nessuna chiamata reale a HA/Spotify.

## Aprire il sito

Doppio click su **`APRI IL SITO.bat`** nella cartella TESI.

## Roadmap MVP (marzo)

1. ~~Simulatore EEG + preprocessing + feature~~
2. ~~Artefatti + ML sklearn (train/predict)~~
3. ~~Web API config profilo/cuffia (scheletro)~~
4. FSM + azioni reali (HA/Spotify) oltre al mock
5. UI web più usabile + calibrazione utente
6. (Opzionale) cuffia fisica meccatronica sulla stessa interfaccia

## Nota account / iPhone

La configurazione utente avverrà via **web app** (usabile da iPhone).
Un account locale servirà a salvare profilo cuffia e mapping azioni —
gratuito e non commerciale, solo personalizzazione.
