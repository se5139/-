@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "PY_CMD=python"
where py >nul 2>nul
if not errorlevel 1 set "PY_CMD=py -3"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
%PY_CMD% scripts\stop_port.py 8520 8521 8522
pause
