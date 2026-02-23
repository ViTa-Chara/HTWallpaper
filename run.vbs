Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)

' Check for uv (system or local)
uv = "uv"
localUv = root & "\.uv\uv.exe"
If fso.FileExists(localUv) Then
  uv = localUv
End If

' Run with uv run
shell.Run """" & uv & """ run --no-dev -m app.tray", 0
