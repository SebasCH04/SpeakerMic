$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir
$python = Join-Path $projectDir ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Error "No se encontro .venv\Scripts\python.exe. Ejecuta primero la instalacion del proyecto."
}

Set-Location $projectDir
& $python -m speakermic tray
