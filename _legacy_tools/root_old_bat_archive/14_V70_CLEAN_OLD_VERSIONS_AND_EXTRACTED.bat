@echo off
setlocal
cd /d "%~dp0"
if exist "scripts\cleanup_old_versions_v68.py" (
  python scripts\cleanup_old_versions_v68.py --yes --current-version 70
) else (
  echo Cleanup helper not found.
)
pause
