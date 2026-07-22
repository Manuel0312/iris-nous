@echo off
:: Richiede diritti amministratore per aprire la porta 8000
cd /d "%~dp0"
net session >nul 2>&1
if %errorLevel% neq 0 (
  echo Richiedo privilegi amministratore...
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0sblocca-rete.ps1"
