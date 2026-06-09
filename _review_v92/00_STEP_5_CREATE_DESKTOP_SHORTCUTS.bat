@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Kakao Emoticon v92 Shortcut Repair

set "PY_CMD="
where py >nul 2>nul
if not errorlevel 1 set "PY_CMD=py -3"
if "%PY_CMD%"=="" (
  where python >nul 2>nul
  if not errorlevel 1 set "PY_CMD=python"
)

if "%PY_CMD%"=="" (
  echo [ERROR] Python was not found.
  echo Install Python 3.10+ or run 00_STEP_2_PORTABLE_INSTALL_NOW.bat first.
  pause
  exit /b 1
)

echo [v92] Creating desktop shortcuts...
%PY_CMD% "%CD%\scripts\create_shortcuts_v92.py" "%CD%"
if errorlevel 1 (
  echo [ERROR] Shortcut creation failed.
  pause
  exit /b 1
)

echo [v92] Shortcut repair completed.
pause
exit /b 0
