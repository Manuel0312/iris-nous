# Bridge nativo telefono (fase C — HARDWARE_CUFFIA)

L’app Flutter in `mobile/` riceve messaggi dalla shell web via `window.IrisNative.postMessage`.

## Azioni già cablate

| Azione shell | Effetto nativo |
|--------------|----------------|
| `openPermissions` | Apre `PermissionsScreen` (chiamate, notifiche, batteria) |
| `ensureCallBridge` | Avvia observer chiamate + heartbeat verso il server |
| `savePairing` | Salva token device fidato |

File: `mobile/lib/screens/site_shell_screen.dart`, plugin Kotlin/Swift in `mobile/android` e `mobile/ios`.

## Gap onesti (OS)

| Capacità | Android APK | iOS IPA |
|----------|-------------|---------|
| Rilevare squillo | Sì (permesso telefono) | Parziale / CallKit present |
| Rispondi / riaggancia cellulare | Limite OS (non sempre) | CallKit se presentato da Iris |
| Notifiche / messaggi | **NotificationListener** (anteprima WhatsApp/Telegram/SMS) + SÌ mostra testo | Limiti iOS: non si legge il contenuto |
| Spotify next | Sì se OAuth collegato | Sì se OAuth collegato |
| Funziona app chiusa | Foreground service chiamate + listener notifiche (con accesso attivo) | Background ristretto |

Idea PDF (HFP/HID): utile **dopo** i permessi app, come livello extra che fa sembrare Iris una cuffia hands-free. Non sostituisce OpenBCI né il server Iris.

## Cosa fare dopo (priorità)

1. Hardening heartbeat + drain comandi OS (`_drainOsCommands`).
2. Documentare in UI Permessi cosa l’OS **non** permette (già parziale).
3. Solo se necessario: modulo BT Classic HFP sul firmware cuffia (fase D/hardware).
