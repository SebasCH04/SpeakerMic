$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir
$logPath = Join-Path $projectDir "dist\SpeakerMic\speakermic.log"

if (-not (Test-Path $logPath)) {
    Write-Host "Todavia no existe log: $logPath"
    Write-Host "Abre dist\SpeakerMic\SpeakerMic.exe una vez y vuelve a correr este script."
    exit 0
}

Get-Content $logPath -Tail 120
