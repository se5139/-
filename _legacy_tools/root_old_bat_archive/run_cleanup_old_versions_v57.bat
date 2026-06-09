@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
echo [v57] Running safe old-version cleanup from installer task...
py -3 "%CD%\scripts\cleanup_old_versions_v57.py" --yes --current-version 57 --protect "%CD%"
if errorlevel 1 (
  python "%CD%\scripts\cleanup_old_versions_v57.py" --yes --current-version 57 --protect "%CD%"
)
exit /b 0
