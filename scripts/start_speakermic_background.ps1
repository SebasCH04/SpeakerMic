$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir
$pythonw = Join-Path $projectDir ".venv\Scripts\pythonw.exe"
$pidFile = Join-Path $projectDir ".speakermic.pid"

if (-not (Test-Path $pythonw)) {
    Write-Error "No se encontro .venv\Scripts\pythonw.exe. Ejecuta primero la instalacion del proyecto."
}

if (Test-Path $pidFile) {
    $existingPid = Get-Content $pidFile -ErrorAction SilentlyContinue
    if ($existingPid -and (Get-Process -Id $existingPid -ErrorAction SilentlyContinue)) {
        exit 0
    }
}

$process = Start-Process `
    -FilePath $pythonw `
    -ArgumentList "-m", "speakermic", "tray" `
    -WorkingDirectory $projectDir `
    -WindowStyle Hidden `
    -PassThru

Set-Content -Path $pidFile -Value $process.Id
