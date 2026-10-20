' Primordial Paradox launcher: runs tools\run.ps1 with no console window at all.
' Double click this file, or make a shortcut to it.
' Exit codes come from run.ps1 and are written to build\last-launch-code.txt so a failure is visible without a console.
Option Explicit

Dim shell, fso, here, script, root, codeFile, code
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

here = fso.GetParentFolderName(WScript.ScriptFullName)
root = fso.GetParentFolderName(here)
script = here & "\run.ps1"
codeFile = root & "\build\last-launch-code.txt"

If Not fso.FileExists(script) Then
    MsgBox "run.ps1 is missing next to this launcher.", 48, "Primordial Paradox"
    WScript.Quit 1
End If

code = shell.Run("powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & script & """", 0, True)

If Not fso.FolderExists(root & "\build") Then fso.CreateFolder(root & "\build")
Dim out
Set out = fso.CreateTextFile(codeFile, True)
out.WriteLine CStr(code)
out.Close

If code <> 0 Then
    MsgBox "The launch stopped with code " & code & ". Details: build\last-build.log", 48, "Primordial Paradox"
End If

WScript.Quit code
