# Collegare Spotify a Iris Nous (iPhone)

Redirect URI da inserire nell’app Spotify Developer:

```text
https://iris-nous.onrender.com/auth/spotify/callback
```

Variabili su Render (Environment):

- `BCI_IOT_SPOTIFY_CLIENT_ID`
- `BCI_IOT_SPOTIFY_CLIENT_SECRET`
- `BCI_IOT_SPOTIFY_REDIRECT_URI` = `https://iris-nous.onrender.com/auth/spotify/callback`
- `BCI_IOT_PUBLIC_URL` = `https://iris-nous.onrender.com`

Dopo aver salvato le variabili: Manual Deploy → Deploy latest commit.
