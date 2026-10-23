"""What's New popup smoke test."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from bci_iot import __version__
from bci_iot.web import create_app
from bci_iot.web.whats_new import whats_new_payload


def test_whats_new_payload_has_version_and_items() -> None:
    payload = whats_new_payload()
    assert payload["version"] == __version__
    assert payload["intro"]
    assert len(payload["entries"]) >= 1
    assert all(item["title"] and (item.get("fix") or item.get("body")) for item in payload["entries"])
    assert all(item.get("problem") for item in payload["entries"])


def test_home_shows_novita_button(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path, session_secret="whats-new")
    page = TestClient(app).get("/", headers={"Accept-Language": "it-IT"})
    assert page.status_code == 200
    assert "whats-new-open" in page.text
    assert "Novità" in page.text
    assert f"Versione {__version__}" in page.text or __version__ in page.text
    assert (
        "Hub «Il tuo telefono»" in page.text
        or "Hub «La tua cuffia»" in page.text
        or "Privacy e chiarezza demo" in page.text
    )
    assert "App: Account senza scorrere" in page.text
    assert "App: testi leggibili su ogni tema e foto" in page.text
    assert "App: niente «Collega telefono» se hai già l’app" in page.text
    assert "App: tutte le Connessioni restano nell’app" in page.text
    assert "App: cuffia nativa, senza aprire il sito" in page.text
    assert "Preview locale: codice subito, senza aspettare la mail" in page.text
    assert "Anteprima locale: codice email a schermo" in page.text
    assert "App: codice email in registrazione, non dopo il login" in page.text
    assert "App: conferma email senza uscire dal telefono" in page.text
    assert "App: cuffia e calibrazione senza uscire dall’app" in page.text
    assert "App telefono: swipe fluido, Account e setup completo" in page.text
    assert "Impostazioni: testo leggibile, tendine insieme, bandiere" in page.text
    assert "Impostazioni e tendine più fluide" in page.text
    assert "Tendine Tema/Lingua senza sovrapposizione" in page.text
    assert "Tema a tendina e foto a tutto schermo" in page.text
    assert "Lingua: menu a tendina vero" in page.text
    assert "Iris: swipe, foto centrate, tastiera senza zoom, rotellina" in page.text
    assert "App telefono = anteprima; /app non è più la destinazione" in page.text
    assert "App Account: dopo Salva vedi il profilo" in page.text
    assert "App Account: foto e prefisso telefono" in page.text
    assert "App: lingue e Novità come sul sito" in page.text
    assert "Ponte PC↔cloud, gate contesti e backup più solido" in page.text
    assert "App: cosa fa Iris e perché iscriversi" in page.text
    assert "App: glass, foto e impostazioni" in page.text
    assert "Anteprima di nuovo visibile" in page.text
    assert "App: foto del sito e account reale" in page.text
    assert "App semplice con popup che ruotano" in page.text
    assert "Anteprima: tre tasti in basso" in page.text
    assert "Anteprima app navigabile prima del download" in page.text
    assert "Testi dell’app più semplici e invitanti" in page.text
    assert "App = sito completo (prima scoperta)" in page.text
    assert "SÌ su messaggio apre WhatsApp + app come il sito" in page.text
    assert "Fix: cancella tutti gli account non va più in errore" in page.text
    assert "Admin: cancella tutti gli account dal Database" in page.text
    assert "Ecosistema su iPad e iPhone + reset account demo" in page.text
    assert "Ecosistema: cuffia animata, store «Prossimamente» e loghi ufficiali" in page.text
    assert "Ecosistema: layout cuffia+telefono e store chiari" in page.text
    assert "Ecosistema: store Google Play / App Store e layout ampio" in page.text
    assert "iPhone: SÌ/NO risponde con CallKit" in page.text
    assert "SÌ/NO può rispondere o rifiutare su Android" in page.text
    assert "Ecosistema centrato, QR download e SÌ/NO dall’app" in page.text
    assert "Foto profilo: tasti chiari e zoom utile" in page.text
    assert "Cuffia virtuale in un tap + telefono più solido" in page.text
    assert "Foto profilo senza ricaricare la pagina" in page.text
    assert "Cuffia senza riconfigurare, associazione pulita, Spotify unico" in page.text
    assert "App liquid glass + QR" in page.text
    assert "Sito e app anche su tablet e telefono" in page.text
    assert "Bentornato più caldo e requisiti password di nuovo verdi" in page.text
    assert "Chiamate APK → In ascolto sul PC, una sola app" in page.text
    assert "Ecosistema a triangolo + app Android allineata" in page.text
    assert "Blu più acceso" in page.text
    assert "Continua e chat: niente più nero" in page.text
    assert "Bottoni e atmosfera finalmente blu" in page.text
    assert "Blu elettrico, più saturo" in page.text
    assert "Cache /app non blocca più i colori nuovi" in page.text
    assert "Blu più vivace" in page.text
    assert "Accento azzurro leggero (niente più verde)" in page.text
    assert "Tendina con foto e icone animate" in page.text
    assert "Menu minimale e Ecosistema a step" in page.text
    assert "Ban: fuori subito, non al prossimo login" in page.text
    assert "Collegamento telefono vero (credenziale)" in page.text
    assert "Pagine telefono più chiare" in page.text
    assert "Colori soft e testo leggibile" in page.text
    assert "App /app in liquid glass" in page.text
    assert "Percorso Apple Developer → TestFlight" in page.text
    assert "Due modi sull’iPhone" in page.text
    assert "App Iris installabile sull’iPhone" in page.text
    assert "Stato e eventi dall’app" in page.text
    assert "App companion Android e iPhone" in page.text
    assert "Chiamate rilevate dall’app → In ascolto" in page.text
    assert "Telefono: associa, Spotify, ponte chiamate" in page.text
    assert "In ascolto, senza accendere nulla" in page.text
    assert "whats-new-body" in page.text
    assert "whats-new-problem" not in page.text
    assert "Versioni precedenti" in page.text or "whats-new-history" in page.text
    assert "SÌ/NO per similarità, non replay" in page.text  # previous release still listed
