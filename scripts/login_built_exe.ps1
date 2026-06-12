$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir
$exe = Join-Path $projectDir "dist\SpeakerMic\SpeakerMic.exe"
$appDir = Split-Path -Parent $exe

if (-not (Test-Path $exe)) {
    Write-Error "No se encontro $exe. Ejecuta .\scripts\build_exe.ps1 primero."
}

Start-Process -FilePath $exe -ArgumentList "spotify-login" -WorkingDirectory $appDir -Wait
Write-Host "Login de Spotify actualizado para el exe."
