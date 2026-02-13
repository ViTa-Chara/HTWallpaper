Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = root
pythonw = root & "\.venv\Scripts\pythonw.exe"
If fso.FileExists(pythonw) Then
  shell.Run "\"" & pythonw & "\" -m app.tray", 0
Else
  shell.Run "pythonw -m app.tray", 0
End If
