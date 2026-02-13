Set shell = CreateObject("WScript.Shell")
root = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
pythonw = root & "\.venv\Scripts\pythonw.exe"
If CreateObject("Scripting.FileSystemObject").FileExists(pythonw) Then
  shell.Run """" & pythonw & """ -m app.tray", 0
Else
  shell.Run "pythonw -m app.tray", 0
End If
