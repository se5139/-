@echo off
setlocal
cd /d "%~dp0"
echo [v57] Safe old-version cleanup helper.
echo This removes old program folders and old shortcuts only. User data folders are backed up first.
choice /C YN /N /M "Clean old versions now? [Y/N]: "
if errorlevel 2 exit /b 0
py -3 "%CD%\scripts\cleanup_old_versions_v57.py" --yes --current-version 57 --protect "%CD%"
if errorlevel 1 (
  python "%CD%\scripts\cleanup_old_versions_v57.py" --yes --current-version 57 --protect "%CD%"
)
pause
