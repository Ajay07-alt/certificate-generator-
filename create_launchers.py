"""
Creates Windows launcher shortcuts (.lnk), batch files (.bat), and VBScript launchers (.vbs)
in both b:/certificate web/1111, b:/certificate web, and the user's Desktop.
"""

import os
import sys
import shutil
from pathlib import Path
import subprocess

app_dir = Path(r"B:\certificate web\1111").resolve()
parent_dir = Path(r"B:\certificate web").resolve()
desktop_dir = Path(os.path.expanduser(r"~\Desktop")).resolve()
icon_path = (app_dir / "app_icon.ico").resolve()
main_py = (app_dir / "main.py").resolve()

# 1. Create Launch.bat in 1111 and parent
bat_content = f"""@echo off
title Visual Bulk Certificate Generator
cd /d "{app_dir}"
echo Launching Visual Bulk Certificate Generator...
python main.py
if errorlevel 1 (
    echo.
    echo Application exited with error. Press any key to close.
    pause >nul
)
"""

(app_dir / "Launch Certificate Generator.bat").write_text(bat_content, encoding="utf-8")
(parent_dir / "Launch Certificate Generator.bat").write_text(bat_content, encoding="utf-8")
print("Created .bat files in 1111 and parent directory.")

# Browser Launch batch file
server_py = (app_dir / "server.py").resolve()
browser_bat_content = f"""@echo off
title Visual Bulk Certificate Generator (Web Edition)
cd /d "{app_dir}"
echo Starting Visual Bulk Certificate Generator Web Server...
python server.py
if errorlevel 1 (
    echo.
    echo Server exited with error. Press any key to close.
    pause >nul
)
"""
(app_dir / "Launch in Browser.bat").write_text(browser_bat_content, encoding="utf-8")
(parent_dir / "Launch in Browser.bat").write_text(browser_bat_content, encoding="utf-8")

# 2. Create Launch_Silent.vbs (launches without showing black console window)
vbs_content = f"""Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "{app_dir}"
WshShell.Run "pythonw.exe \"{main_py}\"", 0, False
Set WshShell = Nothing
"""

(app_dir / "Launch (No Console).vbs").write_text(vbs_content, encoding="utf-8")
(parent_dir / "Launch (No Console).vbs").write_text(vbs_content, encoding="utf-8")

# Browser Silent VBS
browser_vbs = f"""Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "{app_dir}"
WshShell.Run "pythonw.exe \"{server_py}\"", 0, False
Set WshShell = Nothing
"""
(app_dir / "Launch in Browser (No Console).vbs").write_text(browser_vbs, encoding="utf-8")
(parent_dir / "Launch in Browser (No Console).vbs").write_text(browser_vbs, encoding="utf-8")
print("Created .vbs files in 1111 and parent directory.")

# 3. Create Windows Shortcuts (.lnk) with custom icon using PowerShell script file
ps1_script = f"""$WshShell = New-Object -ComObject WScript.Shell
$icon = '{icon_path}'
$target = 'python.exe'
$pyArgs = '"{server_py}"'
$dir = '{app_dir}'

function Make-Shortcut($path, $desc, $arg) {{
    $sc = $WshShell.CreateShortcut($path)
    $sc.TargetPath = $target
    $sc.Arguments = $arg
    $sc.WorkingDirectory = $dir
    $sc.IconLocation = "$icon,0"
    $sc.Description = $desc
    $sc.Save()
}}

Make-Shortcut '{app_dir / "Launch Certificate Generator.lnk"}' 'Launch Desktop Generator' '"{main_py}"'
Make-Shortcut '{parent_dir / "Launch Certificate Generator.lnk"}' 'Launch Desktop Generator' '"{main_py}"'
Make-Shortcut '{app_dir / "Launch in Browser.lnk"}' 'Launch Web Generator in Browser' '"{server_py}"'
Make-Shortcut '{parent_dir / "Launch in Browser.lnk"}' 'Launch Web Generator in Browser' '"{server_py}"'
if (Test-Path '{desktop_dir}') {{
    Make-Shortcut '{desktop_dir / "Launch in Browser.lnk"}' 'Launch Web Generator in Browser' '"{server_py}"'
}}
"""

ps1_file = app_dir / "make_shortcuts.ps1"
ps1_file.write_text(ps1_script, encoding="utf-8")

subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(ps1_file)], check=True)
print("Created .lnk shortcuts with custom icon in folder and on Desktop!")

if ps1_file.exists():
    ps1_file.unlink()
