# Prior EEG per il simulatore / calibrazione / demo impulsi

## Domanda
Esistono già online i “valori EEG” delle parole italiane ACCENDI / SPEGNI / RISPONDI?

## Risposta onesta
**No** come tabella pronta “parola italiana → microvolt”.  
**Sì** come *paradigmi pubblici* che usiamo in modo coerente:

1. **Imagined speech (comandi immaginati)**  
   - Pressel et al. 2016/2017 — 15 soggetti, comandi in spagnolo + vocali  
   - Zenodo: https://zenodo.org/records/19502780  
   - MOABB: `Pressel2016`  
   - Altri: Nieto2022, AguileraRodriguez2025 (MOABB)

2. **Relax vs focus (bande alpha / beta)**  
   - Alpha ~8–12 Hz più forte in rilassamento  
   - Beta ~13–30 Hz più forte in attenzione  
   - Dataset pubblici relax/concentration (es. Mendeley, Muse Zenodo)

## Cosa fa il nostro codice
In `src/bci_iot/acquisition/priors.py` mappiamo:

| Pulsante / colore UI | Prior spettrale (letteratura) | Intent software |
|----------------------|-------------------------------|-----------------|
| SPEGNI / GIALLO      | Alpha dominante               | RELAX           |
| ACCENDI / ROSSO      | Beta dominante                | FOCUS           |
| RISPONDI / VERDE     | Mix decisione / cue           | ACCEPT          |
| RIFIUTA / BLU        | Beta distintivo               | REJECT          |

Poi la **pipeline reale** (feature → ML → router → azione) elabora la finestra.

## Calibrazione sul sito (onestà tesi)

- **Metafora prodotto:** “immagina il colore” (quattro cartelle). Non esiste un EEG “del rosso”.
- **Percorso dati preferito:** una finestra live da **BrainFlow SyntheticBoard** (stessa API di una cuffia fisica supportata). Così il software di cattura è quello che useremo con l’hardware.
- **Fallback:** se BrainFlow non è installato, si usano i prior letterari sopra (banner UI: “prior letterari”, non stream).
- **Cuffia reale:** ancora stub in Config (`Reale — prossimamente`). Contatto elettrodi, impedenza e artefatti restano da validare sul dispositivo.
- **Metriche:** l’accuracy in UI è una stima holdout/leave-one-out sui campioni di calibrazione, **non** “Iris ha letto il cervello”.
- **Online (Render Free):** stream continuo è fragile; la calibrazione completa è consigliata in **locale**. Online resta protocollo/demo account.

## Limiti da dichiarare in commissione

1. Pochi campioni (ripetizioni per colore) → modello fragile al rumore reale.  
2. Il classificatore separa etichette di protocollo, non “parole italiane” dal nulla.  
3. Senza cuffia fisica non si dimostra qualità del segnale (skin contact, muscoli, movimento).  
4. Il passaggio simulatore → board reale cambia soprattutto `board_id` / porta, non la forma della pipeline.
