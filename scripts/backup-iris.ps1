# Crea SEMPRE una nuova cartella backup datata (non sovrascrive le precedenti).
# Destinazione: %USERPROFILE%\Desktop\Iris-backup\backup-YYYY-MM-DD_HH-mm-ss\

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $RepoRoot "src\bci_iot"))) {
  Write-Host "ERRORE: non trovo la cartella TESI (src\bci_iot)." -ForegroundColor Red
  exit 1
}

$stamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$BackupRoot = Join-Path $env:USERPROFILE "Desktop\Iris-backup"
$Dest = Join-Path $BackupRoot ("backup-" + $stamp)

New-Item -ItemType Directory -Path $Dest -Force | Out-Null

Write-Host ""
Write-Host "  Backup Iris Nous" -ForegroundColor Cyan
Write-Host ("  Da:  " + $RepoRoot)
Write-Host ("  A:   " + $Dest)
Write-Host ""

$excludeDirs = @(
  ".venv",
  "venv",
  "__pycache__",
  ".pytest_cache",
  ".mypy_cache",
  ".ruff_cache",
  "node_modules",
  ".dart_tool",
  "build",
  ".gradle",
  "_tmp_apk_check",
  "_tmp_dev_otp",
  "_tmp_dev_otp2",
  "_tmp_dev_otp3",
  "_tmp_email_embed",
  "_tmp_email_shell",
  "_tmp_email_shell2",
  "_tmp_email_shell3",
  "_tmp_embed_smoke",
  "_tmp_embed_smoke2",
  "_tmp_i18n_smoke",
  "_tmp_i18n_smoke2",
  "_tmp_i18n_smoke3",
  "Iris-backup"
)

$robolog = Join-Path $Dest "_backup-robocopy.log"
$rcArgs = @($RepoRoot, $Dest, "/E", "/XD") + $excludeDirs + @(
  "/XF", "*.pyc",
  "/R:1",
  "/W:1",
  "/NFL",
  "/NDL",
  "/NP",
  "/LOG:$robolog"
)

& robocopy @rcArgs | Out-Null
$code = $LASTEXITCODE
if ($code -ge 8) {
  Write-Host ("ERRORE robocopy (codice " + $code + "). Vedi " + $robolog) -ForegroundColor Red
  exit $code
}

$meta = @(
  "Iris Nous backup",
  ("created_utc=" + [DateTime]::UtcNow.ToString("o")),
  ("created_local=" + $stamp),
  ("source=" + $RepoRoot),
  ("dest=" + $Dest),
  ("robocopy_exit=" + $code),
  "note=Nuova cartella a ogni esecuzione; le precedenti restano intatte."
) -join "`r`n"
Set-Content -Path (Join-Path $Dest "_BACKUP_INFO.txt") -Value $meta -Encoding UTF8

$fileCount = (Get-ChildItem -Path $Dest -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
Write-Host ("  OK - " + $fileCount + " file in:") -ForegroundColor Green
Write-Host ("  " + $Dest)
Write-Host ""
Write-Host "  Storico backup:" -ForegroundColor Yellow
Get-ChildItem -Path $BackupRoot -Directory -ErrorAction SilentlyContinue |
  Sort-Object Name -Descending |
  Select-Object -First 8 |
  ForEach-Object { Write-Host ("    " + $_.Name) }
Write-Host ""
