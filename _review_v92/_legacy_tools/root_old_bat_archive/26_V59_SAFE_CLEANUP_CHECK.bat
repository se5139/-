@echo off
setlocal
cd /d "%~dp0"
set "PYEXE="
if exist "%~dp0.venv\Scripts\python.exe" set "PYEXE=%~dp0.venv\Scripts\python.exe"
if not defined PYEXE set "PYEXE=python"
"%PYEXE%" "scripts\v59_safe_cleanup_check.py"
if errorlevel 1 pause
