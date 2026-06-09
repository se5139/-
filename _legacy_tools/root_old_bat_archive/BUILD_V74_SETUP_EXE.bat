@echo off
setlocal
cd /d "%~dp0"
python scripts\build_inno_installer_v74.py
pause
