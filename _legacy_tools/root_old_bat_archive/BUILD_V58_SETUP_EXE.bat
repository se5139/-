@echo off
setlocal
python scripts\build_inno_installer_v58.py
if errorlevel 1 pause
