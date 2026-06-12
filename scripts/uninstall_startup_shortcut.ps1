$startupDir = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startupDir "SpeakerMic.lnk"

if (Test-Path $shortcutPath) {
    Remove-Item $shortcutPath
    Write-Host "Acceso directo eliminado: $shortcutPath"
} else {
    Write-Host "No habia acceso directo de SpeakerMic en Inicio."
}
