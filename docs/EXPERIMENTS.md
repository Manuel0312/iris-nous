# Esperimenti tesi (MoABB-paradigm)

## Cosa abbiamo ora

Comando:

```powershell
.\.venv\Scripts\Activate.ps1
bci-iot experiment --mode surrogate
```

Produce report in `results/experiments/latest.md` (e JSON) con:

- **LOSO** (leave-one-subject-out) — metrica tipica BCI
- **5-fold stratificato** — bound più ottimista su dati pooled
- Confusion matrix e mapping **colori Voilà → intent**

## Onestà scientifica

Il mode `surrogate` **non** scarica Pressel2016: usa i prior spettrali pubblici
già documentati in `EEG_PRIORS.md`, con più “soggetti” sintetici (seed diversi).

Serve a:

1. Dimostrare che feature α/β → regressione logistica gira end-to-end
2. Avere numeri e figure riproducibili per la tesi *come baseline software*
3. Lasciare un hook per MoABB reale (`pip install -e ".[experiments]"`, poi loader)

Il mode `--mode moabb` oggi segnala se `moabb` è installato e spiega che il
loader epoch reale va collegato quando scegliete il dataset definitivo.

## Prossimo (dopo il sito)

Collegare un dataset MoABB reale (es. imagined speech) al `BandPowerExtractor`
e rieseguire le stesse metriche LOSO — senza cambiare la storia del prodotto web.
