@echo off
setlocal
cd /d "%~dp0"
set "PY_CMD="
where py >nul 2>nul
if not errorlevel 1 set "PY_CMD=py -3"
if "%PY_CMD%"=="" (
  where python >nul 2>nul
  if not errorlevel 1 set "PY_CMD=python"
)
if "%PY_CMD%"=="" (echo [ERROR] Python not found.& pause& exit /b 1)
%PY_CMD% scripts\create_shortcuts_v84.py "%CD%"
pause
