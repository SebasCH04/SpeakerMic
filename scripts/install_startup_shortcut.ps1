$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir
$target = Join-Path $scriptDir "start_speakermic_hidden.vbs"
$startupDir = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startupDir "SpeakerMic.lnk"

if (-not (Test-Path $target)) {
    Write-Error "No se encontro $target"
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "wscript.exe"
$shortcut.Arguments = """" + $target + """"
$shortcut.WorkingDirectory = $projectDir
$shortcut.WindowStyle = 7
$shortcut.Description = "Start SpeakerMic in the background"
$shortcut.Save()

Write-Host "Acceso directo creado: $shortcutPath"
