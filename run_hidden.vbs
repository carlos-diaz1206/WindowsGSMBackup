' WinGSM Backup Manager - Hidden Console Launcher
' This script launches the application without showing any console window
Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Get the directory where this script is located
strScriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)

' Check if Python is available
strCommand = "cmd /c python --version"
intReturn = objShell.Run(strCommand, 0, True)

If intReturn <> 0 Then
    MsgBox "Python is not installed or not in PATH." & vbCrLf & vbCrLf & _
           "Please install Python 3.8 or later from https://www.python.org/downloads/" & vbCrLf & _
           "Make sure to check 'Add Python to PATH' during installation.", _
           vbCritical, "Python Not Found"
    WScript.Quit 1
End If

' Check if main.py exists
strMainPy = strScriptDir & "\main.py"
If Not objFSO.FileExists(strMainPy) Then
    MsgBox "main.py not found in the script directory." & vbCrLf & vbCrLf & _
           "Please make sure this script is in the project directory.", _
           vbCritical, "File Not Found"
    WScript.Quit 1
End If

' Launch the application with hidden console window
' Using pythonw.exe if available, otherwise python.exe with hidden window
strCommand = "pythonw """ & strMainPy & """"
intReturn = objShell.Run(strCommand, 0, False)

If intReturn <> 0 Then
    ' If pythonw failed, try regular python with hidden window
    strCommand = "python """ & strMainPy & """"
    objShell.Run strCommand, 0, False
End If

WScript.Quit 0

