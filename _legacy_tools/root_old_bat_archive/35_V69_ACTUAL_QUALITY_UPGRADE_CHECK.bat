@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" scripts\v69_actual_quality_upgrade_check.py
) else (
  python scripts\v69_actual_quality_upgrade_check.py
)
pause
