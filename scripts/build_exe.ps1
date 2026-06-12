$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir
$python = Join-Path $projectDir ".venv\Scripts\python.exe"
$distAppDir = Join-Path $projectDir "dist\SpeakerMic"

if (-not (Test-Path $python)) {
    Write-Error "No se encontro .venv\Scripts\python.exe. Ejecuta primero la instalacion del proyecto."
}

Set-Location $projectDir

Get-Process -Name "SpeakerMic" -ErrorAction SilentlyContinue |
    Stop-Process -Force

$runningBuiltProcesses = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
        $_.ExecutablePath -and
        $_.ExecutablePath.StartsWith($distAppDir, [System.StringComparison]::OrdinalIgnoreCase)
    }

foreach ($process in $runningBuiltProcesses) {
    Stop-Process -Id $process.ProcessId -Force
}

& $python -m PyInstaller --version 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller no esta instalado. Instalando dependencias de build..."
    & $python -m pip install -r requirements-build.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Error "No se pudo instalar PyInstaller."
    }
}

& $python -m PyInstaller SpeakerMic.spec --noconfirm --clean
if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller fallo."
}

if (-not (Test-Path $distAppDir)) {
    Write-Error "PyInstaller no creo $distAppDir"
}

if (Test-Path "config.toml") {
    Copy-Item "config.toml" $distAppDir -Force
} elseif (Test-Path "config.example.toml") {
    Copy-Item "config.example.toml" (Join-Path $distAppDir "config.toml") -Force
}

if (Test-Path ".speakermic_tokens.json") {
    Copy-Item ".speakermic_tokens.json" $distAppDir -Force
}

if (Test-Path "models") {
    robocopy "models" (Join-Path $distAppDir "models") /E /NFL /NDL /NJH /NJS /NC /NS | Out-Null
    if ($LASTEXITCODE -le 7) {
        $global:LASTEXITCODE = 0
    }
}

Write-Host "Build listo: $distAppDir\SpeakerMic.exe"
