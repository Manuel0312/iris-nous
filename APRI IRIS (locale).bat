@echo off
cd /d "%~dp0"
title Iris Nous — locale

if not exist ".venv\Scripts\uvicorn.exe" (
  echo Ambiente non pronto. Apri Cursor e chiedi di reinstallare il venv.
  pause
  exit /b 1
)

echo.
echo  ========================================
echo   Iris Nous — sito LOCALE (con reload)
echo  ========================================
echo.
echo  ATTENZIONE: questo database e' SOLO del PC.
echo  L'account del telefono / Spotify e' sul sito ONLINE:
echo    https://iris-nous.onrender.com/
echo  Per lo stesso account, usa APRI IL SITO.bat
echo.
echo  Le modifiche ai file si vedono subito.
echo  Lascia questa finestra APERTA.
echo.
echo  PC:       http://127.0.0.1:8000/
echo  Telefono (stessa Wi-Fi):
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
  for /f "tokens=1" %%b in ("%%a") do echo            http://%%b:8000/
)
echo.
echo  Login admin: admin / admin123
echo.

start "" "http://127.0.0.1:8000/"
".venv\Scripts\uvicorn.exe" bci_iot.web.app:app --host 0.0.0.0 --port 8000 --reload
