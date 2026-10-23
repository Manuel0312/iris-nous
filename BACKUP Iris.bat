@echo off
title Iris Nous — Backup datato
cd /d "%~dp0"
echo.
echo  ========================================
echo   Backup Iris (nuova cartella con data)
echo  ========================================
echo  Destinazione:
echo    %%USERPROFILE%%\Desktop\Iris-backup\backup-AAAA-MM-GG_HH-mm-ss
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\backup-iris.ps1"
echo.
pause
