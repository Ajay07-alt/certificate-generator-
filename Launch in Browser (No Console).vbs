Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "B:\certificate web\1111"
WshShell.Run "pythonw.exe "B:\certificate web\1111\server.py"", 0, False
Set WshShell = Nothing
