# Imposta i secret GitHub per il relay mail Iris (dopo: gh auth login)
# Uso: .\scripts\setup_github_mail_secrets.ps1

$ErrorActionPreference = "Stop"
$repo = "Manuel0312/iris-nous"
$user = "noreply.irisnous@gmail.com"

# Password app da messaging.json locale (non stampata)
$msgPath = Join-Path $PSScriptRoot "..\data\messaging.json"
if (-not (Test-Path $msgPath)) {
  Write-Error "Manca data/messaging.json con smtp_password"
}
$cfg = Get-Content $msgPath -Raw | ConvertFrom-Json
$password = [string]$cfg.smtp_password
if (-not $password) { Write-Error "smtp_password vuota in messaging.json" }

gh auth status
Write-Host "Imposto secret su $repo ..."
$password | gh secret set IRIS_SMTP_PASSWORD --repo $repo
$user | gh secret set IRIS_SMTP_USER --repo $repo
$user | gh secret set IRIS_SMTP_FROM --repo $repo

Write-Host ""
Write-Host "Secret SMTP ok."
Write-Host "Ora crea un token classic (permesso repo) e:"
Write-Host "  1) salvalo su Render come BCI_IOT_GITHUB_MAIL_TOKEN"
Write-Host "  2) oppure: gh secret non basta per Render — va nel dashboard Render"
Write-Host ""
Write-Host "Apri creazione token:"
Write-Host '  https://github.com/settings/tokens/new?scopes=repo&description=Iris-Nous-mail-relay'
