# Deploy Iris Nous (hosting gratuito, PC spento)

## Host consigliato: Render (free)
1. Codice su GitHub
2. Su https://dashboard.render.com → New → Blueprint → seleziona il repo
3. Imposta `BCI_IOT_ADMIN_PASSWORD` se non generata
4. URL tipo `https://iris-nous.onrender.com`

Il piano free può “addormentarsi” dopo inattività (~15 min): al primo click si riaccende in ~30–60s. Resta raggiungibile da chiunque senza PC acceso.

## Variabili
- `BCI_IOT_SESSION_SECRET` (generata da Render)
- `BCI_IOT_ADMIN_USERNAME` / `BCI_IOT_ADMIN_PASSWORD`
- `BCI_IOT_HTTPS=1`
- `BCI_IOT_DATA_DIR=/data`

## Spotify (musica sul telefono)
Vedi `docs/SPOTIFY.md`. Serve Spotify Premium + app su [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard).
