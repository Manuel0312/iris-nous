# Riferimento rapido — cuffia reale Iris

Guida unificata (PDF + repo): **`docs/HARDWARE_CUFFIA.md`**.
Qui sotto solo BOM / stampante / canali.

## Stampante

| | |
|---|---|
| Modello | Bambu Lab A1 mini |
| Volume | 180 × 180 × 180 mm |
| Ultracortex | Quattro quarti (Front/Back × Left/Right). Le metà ufficiali chiedono ~210 mm e non entrano. Lato piatto sul piano, supporti e brim. Non scalare. |
| Materiale prototipo | PLA (poi valutare PETG per tenuta) |
| Ordine | Bundle Print-It-Yourself 8 ch, shop.openbci.com, $1799 (ott 2026) + spedizione + ~25% import EU |

## OpenBCI (ordini tipici, USD shop — verificare + dazi EU)

| Pezzo | Ruolo | Ordine di grandezza |
|---|---|---|
| Ganglion 4 ch | Board budget, BrainFlow | ~$625 |
| Cyton 8 ch | Board più seria | ~$1249 |
| Cyton + Daisy 16 ch | Tanti canali | ~$2499 |
| Ultracortex Mark IV (assemblata) | Scocca pronta | da ~$500–1000+ |
| Complete Ultracortex | Tutto pronto | ~$2999 |
| EEG Headband Kit | Alternativa fascia | ~$350 |
| Holder / comb electrodes | Non stampare a casa i pezzi critici Mark IV | shop OpenBCI |
| STL Ultracortex | Frame open-source | GitHub `OpenBCI/Ultracortex` |

## BrainFlow (già usato in Iris)

- Oggi: `SYNTHETIC_BOARD` via `BrainFlowSyntheticSource`.
- Target: `GANGLION_BOARD` / `CYTON_BOARD` / Daisy (+ serial/BLE params).
- Muse è supportato da BrainFlow ma **non** è la scelta Iris per cuffia modificabile.

## Canali (decisione 8 ottobre 2026)

Board ordinabile: **Cyton 8 ch**. Upgrade futuro: **Daisy** sulla stessa Cyton → 16 ch.
Ganglion non è la scelta Iris.

Mappa di partenza (da raffinare in CAD): **Fp1, Fp2, F3, F4, C3, Cz, C4, Pz**
+ earclip riferimento/bias. Il sì/no sta su C3/Cz/C4; Fp1/Fp2 servono a scartare i blink.

## Soft agent attuale

`HeadsetAgent` gestisce power / wear / contact / impulsi in memoria.
Con hardware reale: stessa UX, `signal_path` da `simulated` → `brainflow_openbci`
quando lo stream passa QC.

## Link utili

- https://shop.openbci.com/
- https://docs.openbci.com/AddOns/Headwear/MarkIV/
- https://github.com/OpenBCI/Ultracortex
- https://brainflow.readthedocs.io/en/stable/SupportedBoards.html
