# Permessi Iris Nous (riassunto IT)

Vedi anche `../README.md`. Richiesta graduale in app.

## Android

1. **Internet** — collegarsi a Iris  
2. **Stato telefono** (`READ_PHONE_STATE`) — *Per capire se arriva una chiamata…* (non rispondere/rifiutare)  
3. **Numeri** (`READ_PHONE_NUMBERS`) — opzionale  
4. **Notifiche** (`POST_NOTIFICATIONS`, Android 13+) — avvisi eventi  
5. **Servizio in primo piano** — heartbeat / osservazione in background  
6. **SMS** — *non richiesto* in questa versione  

## iPhone

1. **CXCallObserver** — rilevare squillo/fine (non answer/reject cellulare)  
2. **Notifiche** — avvisi  
3. **Background fetch/processing** — heartbeat  
4. **Microfono / Tracking / SMS** — non usati  
