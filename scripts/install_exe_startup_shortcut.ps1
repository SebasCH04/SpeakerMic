$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir
$exe = Join-Path $projectDir "dist\SpeakerMic\SpeakerMic.exe"
$startupDir = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startupDir "SpeakerMic.lnk"

if (-not (Test-Path $exe)) {
    Write-Error "No se encontro $exe. Ejecuta .\scripts\build_exe.ps1 primero."
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $exe
$shortcut.WorkingDirectory = Split-Path -Parent $exe
$shortcut.WindowStyle = 7
$shortcut.Description = "Start SpeakerMic"
$shortcut.Save()

Write-Host "Acceso directo creado: $shortcutPath"
