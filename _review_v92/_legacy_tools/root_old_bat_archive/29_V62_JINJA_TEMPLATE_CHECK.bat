@echo off
setlocal
cd /d "%~dp0"
set "PYEXE=python"
if exist "%~dp0.venv\Scripts\python.exe" set "PYEXE=%~dp0.venv\Scripts\python.exe"
"%PYEXE%" "%~dp0scripts\v62_jinja_template_check.py"
pause
