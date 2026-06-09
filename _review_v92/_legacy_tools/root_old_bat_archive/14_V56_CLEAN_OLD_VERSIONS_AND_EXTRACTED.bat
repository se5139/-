@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo [v56] Safe old-version cleanup helper.
echo This removes old program folders and old shortcuts only.
echo User data subfolders are backed up before cleanup.
echo.
set "CONFIRM=N"
set /p CONFIRM=Type Y to clean old versions, Enter to cancel: 
if /I not "%CONFIRM%"=="Y" (
  echo Cleanup cancelled.
  pause
  exit /b 0
)
py -3 "%CD%\scripts\cleanup_old_versions_v56.py" --yes --current-version 56 --protect "%CD%"
if errorlevel 1 (
  python "%CD%\scripts\cleanup_old_versions_v56.py" --yes --current-version 56 --protect "%CD%"
)
pause
exit /b 0
