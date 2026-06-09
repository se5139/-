@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PY_CMD="

title Kakao Emoticon v100 Sync State Export

echo.
echo ============================================================
echo  Kakao Emoticon Maker v100 Clean - Sync State Export
echo ============================================================
echo This creates a ZIP for continuing your memory/results on another PC.
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

%PY_CMD% scripts\export_sync_state.py
if errorlevel 1 (
  echo.
  echo [FAIL] Sync state export failed.
  pause
  exit /b 1
)

echo.
echo [OK] Sync state export complete.
echo Check the release folder for sync_state_export_latest.zip.
pause
exit /b 0
