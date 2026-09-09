# Deploy Iris Nous (hosting gratuito, PC spento)

## Host consigliato: Render (free)
1. Codice su GitHub
2. Su https://dashboard.render.com → New → Blueprint → seleziona il repo
3. Imposta `BCI_IOT_ADMIN_PASSWORD` a `admin123` (stessa del PC). Se era già
   una password casuale, cambiala nel dashboard e fai **Manual Deploy**:
   all’avvio Iris allinea la password admin a quella della variabile.
4. URL: `https://iris-nous.onrender.com`

Il piano free può “addormentarsi” dopo inattività (~15 min): al primo click si riaccende in ~30–60s. Resta raggiungibile da chiunque senza PC acceso.

**Due siti, due database.** Il PC locale (`APRI IRIS (locale).bat`) e il sito
online **non condividono** gli account. Telefono + Spotify + stesso login:
usa sempre l’URL online anche dal PC (`APRI IL SITO.bat`).

Accesso admin sul sito online: username `admin`, password `admin123`
(o il valore di `BCI_IOT_ADMIN_PASSWORD` nel dashboard Render). All’avvio
Iris ricrea/allinea questo account, anche se il disco free si è svuotato.

Sul piano free i file in `/data` si perdono quando il servizio si spegne.
Per tenere gli account tra un riavvio e l’altro serve un disco persistente
(istanza a pagamento su Render → Disk mount `/data`).

## Variabili
- `BCI_IOT_SESSION_SECRET` (generata da Render)
- `BCI_IOT_ADMIN_USERNAME=admin`
- `BCI_IOT_ADMIN_PASSWORD=admin123`
- `BCI_IOT_HTTPS=1`
- `BCI_IOT_DATA_DIR=/data`
- `BCI_IOT_PUBLIC_URL=https://iris-nous.onrender.com`

## Spotify (musica sul telefono)
Vedi `docs/SPOTIFY.md`. Serve Spotify Premium + app su [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard).

## Mail Iris Nous (recupero password — solo email)
Come Apple/Google, Iris manda da un mittente brandizzato (**Iris Nous**). L’SMS per ora non si usa.

Collega **una volta** un servizio di posta:
1. **Resend** (consigliato): chiave `BCI_IOT_RESEND_API_KEY` oppure Admin → **Mail Iris Nous**
2. **Gmail SMTP** (alternativa): `BCI_IOT_SMTP_*` oppure stesso pannello

Mittente: `BCI_IOT_MAIL_FROM` (es. `noreply@iris-nous.app`). Senza dominio verificato su Resend, usa il mittente di prova del provider.

In locale senza provider il codice compare ancora nel sito. In produzione: `BCI_IOT_REQUIRE_REAL_OTP=1`.
