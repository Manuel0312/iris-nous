# Scarica l'ultimo IPA e/o APK da GitHub Actions e sovrascrive i path canonici.
# Uso:
#   .\scripts\fetch-mobile-builds.ps1            # entrambi se disponibili
#   .\scripts\fetch-mobile-builds.ps1 -IpaOnly
#   .\scripts\fetch-mobile-builds.ps1 -ApkOnly
#   .\scripts\fetch-mobile-builds.ps1 -IpaRunId 38737364339

param(
  [switch]$IpaOnly,
  [switch]$ApkOnly,
  [string]$Repo = "Manuel0312/iris-nous",
  [string]$IpaRunId = "",
  [string]$ApkRunId = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$deskRoot = Join-Path ([Environment]::GetFolderPath("Desktop")) "app iris"
$ipaDir = Join-Path $deskRoot "iphone"
$apkDir = Join-Path $deskRoot "android"
$ipaDest = Join-Path $ipaDir "IrisNous-unsigned.ipa"
$apkDest = Join-Path $apkDir "IrisNous.apk"
# Mirror opzionale nel repo (stesso overwrite)
$ipaRepo = Join-Path $root "IrisNous-ipa\IrisNous-unsigned.ipa"
$apkRepo = Join-Path $root "IrisNous-apk\IrisNous.apk"

function Ensure-Dir([string]$path) {
  New-Item -ItemType Directory -Force -Path $path | Out-Null
}

function Latest-RunId([string]$workflow) {
  $json = gh run list --repo $Repo --workflow $workflow --limit 1 --json databaseId,conclusion,status | ConvertFrom-Json
  if (-not $json) { throw "Nessuna run per $workflow" }
  $run = $json[0]
  if ($run.status -ne "completed" -or $run.conclusion -ne "success") {
    throw "Ultima run $workflow non riuscita (status=$($run.status) conclusion=$($run.conclusion) id=$($run.databaseId))"
  }
  return [string]$run.databaseId
}

function Fetch-Ipa([string]$runId) {
  Ensure-Dir $ipaDir
  $tmp = Join-Path $ipaDir "_dl_tmp"
  if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
  New-Item -ItemType Directory -Force -Path $tmp | Out-Null
  gh run download $runId --repo $Repo --name iris-nous-ios-ipa-unsigned --dir $tmp
  $found = Get-ChildItem $tmp -Recurse -Filter "*.ipa" | Select-Object -First 1
  if (-not $found) { throw "IPA non trovata nell'artifact della run $runId" }
  if (Test-Path $ipaDest) { Remove-Item $ipaDest -Force }
  Copy-Item $found.FullName $ipaDest -Force
  Ensure-Dir (Split-Path $ipaRepo)
  Copy-Item $ipaDest $ipaRepo -Force
  Remove-Item $tmp -Recurse -Force
  Write-Host "OVERWRITE_IPA=$ipaDest ($([math]::Round((Get-Item $ipaDest).Length/1MB, 2)) MB) run=$runId"
}

function Fetch-Apk([string]$runId) {
  Ensure-Dir $apkDir
  $tmp = Join-Path $apkDir "_dl_tmp"
  if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
  New-Item -ItemType Directory -Force -Path $tmp | Out-Null
  gh run download $runId --repo $Repo --name iris-nous-android-apk --dir $tmp
  $found = Get-ChildItem $tmp -Recurse -Filter "*.apk" | Select-Object -First 1
  if (-not $found) { throw "APK non trovato nell'artifact della run $runId" }
  if (Test-Path $apkDest) { Remove-Item $apkDest -Force }
  Copy-Item $found.FullName $apkDest -Force
  Ensure-Dir (Split-Path $apkRepo)
  Copy-Item $apkDest $apkRepo -Force
  Remove-Item $tmp -Recurse -Force
  Write-Host "OVERWRITE_APK=$apkDest ($([math]::Round((Get-Item $apkDest).Length/1MB, 2)) MB) run=$runId"
}

$doIpa = -not $ApkOnly
$doApk = -not $IpaOnly
$apkRunUsed = ""
$ipaRunUsed = ""

if ($doIpa) {
  $id = if ($IpaRunId) { $IpaRunId } else { Latest-RunId "ios-ipa-sideload.yml" }
  $ipaRunUsed = $id
  Fetch-Ipa $id
}
if ($doApk) {
  $id = if ($ApkRunId) { $ApkRunId } else { Latest-RunId "android-apk.yml" }
  $apkRunUsed = $id
  Fetch-Apk $id
}

$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }
$manifestScript = Join-Path $root "scripts\update-mobile-manifest.py"
$manifestArgs = @($manifestScript)
if ($doApk -and (Test-Path $apkDest)) {
  $manifestArgs += @("--apk", $apkDest, "--apk-run", $apkRunUsed)
}
if ($doIpa -and (Test-Path $ipaDest)) {
  $manifestArgs += @("--ipa", $ipaDest, "--ipa-run", $ipaRunUsed)
}
& $py @manifestArgs
Write-Host "UPDATED_MANIFEST=$($root)\src\bci_iot\web\static\mobile\build-manifest.json"
