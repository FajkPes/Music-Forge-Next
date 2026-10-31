@echo off
setlocal
cd /d "%~dp0"
title Music Forge Next
if not exist ".venv\Scripts\python.exe" (
  echo Chybi lokalni Python prostredi. Podivejte se do README.md.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" server.py --open
if errorlevel 1 pause
