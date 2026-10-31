@echo off
setlocal
cd /d "%~dp0"
py -3.12 -m venv .venv
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto fail
echo Instalace dokoncena. Spustte Spustit Music Forge.cmd.
pause
exit /b 0
:fail
echo Instalace selhala. Nainstalujte Python 3.12 x64 a opakujte.
pause
exit /b 1
