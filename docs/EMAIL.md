# Mail Iris Nous + Gmail (guida tesi)

## Indirizzo già in uso
| Campo | Valore |
|--------|--------|
| Gmail Iris | `noreply.irisnous@gmail.com` |
| Nome visualizzato | **Iris Nous** (fisso nel software) |
| Host SMTP | `smtp.gmail.com` |
| Porta | `587` |

## Locale (già ok se ricevi le mail)
1. File `data/messaging.json` e/o `.env` con SMTP Gmail `noreply…`
2. Oppure admin → **Mail Iris Nous** → Attiva
3. Avvio: `APRI IRIS (locale).bat` → http://127.0.0.1:8000/

## Online = stesso mittente (Render free)

Su Render le porte SMTP spesso sono **bloccate**. Iris usa un **relay GitHub Actions**
che spedisce dalla stessa Gmail: il cliente vede ancora
`Iris Nous <noreply.irisnous@gmail.com>`.

### A) Secret sul repo GitHub `Manuel0312/iris-nous`
Settings → Secrets and variables → Actions → New repository secret:

| Secret | Valore |
|--------|--------|
| `IRIS_SMTP_USER` | `noreply.irisnous@gmail.com` |
| `IRIS_SMTP_PASSWORD` | password per le app Gmail (16 lettere) |
| `IRIS_SMTP_FROM` | `noreply.irisnous@gmail.com` |

Il workflow `.github/workflows/iris-mail.yml` li usa già.

### B) Token GitHub per far partire il relay da Render
1. GitHub → Settings → Developer settings → [Personal access tokens](https://github.com/settings/tokens)
2. Classic token con permesso **`repo`** (serve `repository_dispatch`)
3. Copia il token (`ghp_…`)

### C) Variabili su Render (dashboard → iris-nous → Environment)
| Key | Valore |
|-----|--------|
| `BCI_IOT_GITHUB_MAIL_REPO` | `Manuel0312/iris-nous` |
| `BCI_IOT_GITHUB_MAIL_TOKEN` | il `ghp_…` del passo B |
| `BCI_IOT_MAIL_FROM` | `noreply.irisnous@gmail.com` |
| `BCI_IOT_SMTP_USER` | `noreply.irisnous@gmail.com` |
| `BCI_IOT_SMTP_FROM` | `noreply.irisnous@gmail.com` |
| `BCI_IOT_SMTP_PASSWORD` | stessa password app (utile a Brevo/fallback; il relay usa i secret GitHub) |

Poi **Manual Deploy** → Deploy latest commit.

### Verifica
1. Registrazione (o recupero password) sul sito online
2. GitHub → Actions → workflow **iris-mail** deve risultare verde
3. In posta: mittente **Iris Nous \<noreply.irisnous@gmail.com\>**

## Cosa ricevono gli utenti
1. **Dopo registrazione:** conferma iscrizione + codice/link
2. **Recupero password:** codice a 6 caratteri

Finché in locale Gmail non è collegata, link/codice compaiono nel sito per i test.
