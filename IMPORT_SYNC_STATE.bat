@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PY_CMD="

title Kakao Emoticon v100 Sync State Import

echo.
echo ============================================================
echo  Kakao Emoticon Maker v100 Clean - Sync State Import
echo ============================================================
echo This imports memory and recent outputs into this app folder.
echo.

where py >nul 2>nul
if not errorlevel 1 set "PY_CMD=py -3"

if "%PY_CMD%"=="" (
  where python >nul 2>nul
  if not errorlevel 1 set "PY_CMD=python"
)

if "%PY_CMD%"=="" (
  echo [FAIL] Python was not found.
  echo Install Python 3.10+ and enable "Add Python to PATH".
  pause
  exit /b 1
)

%PY_CMD% scripts\import_sync_state.py
if errorlevel 1 (
  echo.
  echo [FAIL] Sync state import failed.
  pause
  exit /b 1
)

echo.
echo [OK] Sync state import complete.
echo You can now run START_HERE.bat.
pause
exit /b 0
