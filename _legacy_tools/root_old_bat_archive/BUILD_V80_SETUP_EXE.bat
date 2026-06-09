@echo off
setlocal
cd /d "%~dp0"
python scripts\build_inno_installer_v80.py
pause
