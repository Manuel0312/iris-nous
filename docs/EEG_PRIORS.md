# Prior EEG per il simulatore / demo impulsi

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

| Pulsante | Prior spettrale (letteratura) | Intent software |
|----------|-------------------------------|-----------------|
| SPEGNI   | Alpha dominante               | RELAX           |
| ACCENDI  | Beta dominante                | FOCUS           |
| RISPONDI | Mix decisione / cue           | ACCEPT          |
| RIFIUTA  | Beta distintivo               | REJECT           |

Poi la **pipeline reale** (feature → ML → router → azione) elabora la finestra.

La **scansione sul tuo cervello** (Face ID-style) resta il passo successivo per personalizzare.
