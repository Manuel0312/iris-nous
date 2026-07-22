# Sblocca la porta 8000 sul firewall Windows (necessario per il telefono).
# Esegui con: tasto destro → Esegui con PowerShell come amministratore
# oppure doppio click su sblocca-rete.bat

$ErrorActionPreference = "Stop"
$port = 8000
$ruleName = "BCI-IoT Web Config (TCP $port)"

$existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Regola gia presente: $ruleName" -ForegroundColor Yellow
} else {
    New-NetFirewallRule `
        -DisplayName $ruleName `
        -Direction Inbound `
        -Protocol TCP `
        -LocalPort $port `
        -Action Allow `
        -Profile Any `
        -Description "Permette ad altri dispositivi sulla stessa rete di aprire la web app BCI." | Out-Null
    Write-Host "Regola creata: $ruleName (porta $port, tutti i profili)" -ForegroundColor Green
}

Write-Host ""
Write-Host "Ora:"
Write-Host "1) Avvia start-web.bat"
Write-Host "2) Sul telefono (stessa Wi-Fi/hotspot) apri il link in ACCESSO_WEB.txt"
Write-Host ""
pause
