@echo off
setlocal
cd /d "%~dp0"
python scripts\v60_installer_build_fix_check.py
if errorlevel 1 pause
