@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo [legacy] Running v43 installer stability check...
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe scripts\v43_installer_stability_check.py
) else (
  py -3 scripts\v43_installer_stability_check.py
)
pause
