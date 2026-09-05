from pathlib import Path
import os
import re
import shutil

from fastapi.testclient import TestClient

from bci_iot.web import create_app

os.environ["BCI_IOT_ENV"] = "dev"
tmp = Path("data/_qa_confirm3")
if tmp.exists():
    shutil.rmtree(tmp)
tmp.mkdir(parents=True)
app = create_app(data_dir=tmp, session_secret="x")
client = TestClient(app)
client.post(
    "/register",
    data={"username": "nuova2", "email": "nuova2@gmail.com", "password": "Segreta123"},
    follow_redirects=False,
)
page = client.get("/attendi-conferma-email")
assert 'name="code"' in page.text, page.text[:800]
match = re.search(r"codice ([A-Z0-9]{6})", page.text)
assert match, page.text[400:1400]
code = match.group(1)
resp = client.post(
    "/attendi-conferma-email", data={"code": code}, follow_redirects=False
)
print("confirm_code", resp.status_code, resp.headers.get("location"))
assert "/anagrafica" in (resp.headers.get("location") or "")
print("OK", code)
