@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Kakao Emoticon v82 Stepwise Build Check
set "PY_CMD="
where py >nul 2>nul
if not errorlevel 1 set "PY_CMD=py -3"
if "%PY_CMD%"=="" (
  where python >nul 2>nul
  if not errorlevel 1 set "PY_CMD=python"
)
if "%PY_CMD%"=="" (
  echo [ERROR] Python not found.
  pause
  exit /b 1
)
%PY_CMD% scripts82_stepwise_build_check.py
set "ERR=%ERRORLEVEL%"
echo.
pause
exit /b %ERR%
