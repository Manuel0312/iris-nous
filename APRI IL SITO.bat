@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\uvicorn.exe" (
  echo Ambiente non pronto. Apri Cursor e chiedi di reinstallare il venv.
  pause
  exit /b 1
)

echo Avvio del sito in corso...
echo Lascia questa finestra aperta.
echo.
echo Sul PC:     http://127.0.0.1:8000/
echo Sul telefono (stessa Wi-Fi del PC), apri:
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
  for /f "tokens=1" %%b in ("%%a") do echo           http://%%b:8000/
)
echo.
echo Se non si apre dal telefono: firewall Windows puo bloccare la porta 8000.
echo.

start "" "http://127.0.0.1:8000/"
".venv\Scripts\uvicorn.exe" bci_iot.web.app:app --host 0.0.0.0 --port 8000 --reload
