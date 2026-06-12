$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir
$exe = Join-Path $projectDir "dist\SpeakerMic\SpeakerMic.exe"

if (-not (Test-Path $exe)) {
    Write-Error "No se encontro $exe. Ejecuta .\scripts\build_exe.ps1 primero."
}

Start-Process -FilePath $exe -WorkingDirectory (Split-Path -Parent $exe)
