Set shell = CreateObject("WScript.Shell")
root = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
launcher = root & "\run.bat"
If CreateObject("Scripting.FileSystemObject").FileExists(launcher) Then
  shell.Run """" & launcher & """", 0
Else
  shell.Run "cmd /c """" & root & "\run.bat""""", 0
End If
