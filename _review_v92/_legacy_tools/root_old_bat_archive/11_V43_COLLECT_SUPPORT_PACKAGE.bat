@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo [legacy] Collecting v43 support package...
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe scripts\v43_installer_stability_check.py --support
) else (
  py -3 scripts\v43_installer_stability_check.py --support
)
pause
