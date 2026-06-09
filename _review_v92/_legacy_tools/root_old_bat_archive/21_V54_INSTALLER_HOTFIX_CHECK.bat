@echo off
setlocal EnableExtensions
cd /d "%~dp0"
python "scripts\v54_installer_hotfix_check.py"
if errorlevel 1 (
  echo [v54] Check FAILED.
  pause
  exit /b 1
)
echo [v54] Check PASS.
pause
