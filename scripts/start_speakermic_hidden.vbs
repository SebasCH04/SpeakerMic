Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
projectDir = fso.GetParentFolderName(scriptDir)
launcher = scriptDir & "\start_speakermic_background.ps1"

If Not fso.FileExists(launcher) Then
  MsgBox "No se encontro scripts\start_speakermic_background.ps1.", 16, "SpeakerMic"
  WScript.Quit 1
End If

shell.CurrentDirectory = projectDir
command = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & launcher & """"
shell.Run command, 0, False
