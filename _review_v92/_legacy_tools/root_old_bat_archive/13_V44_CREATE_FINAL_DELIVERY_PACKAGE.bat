@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo [v48] Running integration check before packaging...
python scripts\v44_full_integration_check.py
if errorlevel 1 (
  echo [ERROR] Integration check failed. Packaging should stop.
  pause
  exit /b 1
)
echo [OK] Integration check passed. Zip this folder for delivery.
pause
