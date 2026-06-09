@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo [v48] Running full integration check based on v44 engine...
python scripts\v44_full_integration_check.py
if errorlevel 1 (
  echo [ERROR] Integration check failed.
  echo Check outputs\v44_final_integration.
  pause
  exit /b 1
)
echo [OK] Integration check completed.
pause
