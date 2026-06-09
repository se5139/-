@echo off
cd /d "%~dp0"
echo [v86] Compact workflow root check started.
set PY_CMD=python
where py >nul 2>nul && set PY_CMD=py -3
%PY_CMD% scripts\v86_compact_workflow_check.py
if errorlevel 1 (
  echo [v86] Check failed.
  pause
  exit /b 1
)
echo [v86] Check PASS.
pause
