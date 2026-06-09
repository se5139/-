@echo off
cd /d "%~dp0"
echo [v85] Compact workflow root check started.
python scripts\v85_compact_workflow_check.py
if errorlevel 1 (
  echo [v85] Check failed.
  pause
  exit /b 1
)
echo [v85] Check PASS.
pause
