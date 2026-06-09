@echo off
setlocal
cd /d "%~dp0"
python scripts\v57_sidebar_navigation_check.py
if errorlevel 1 (
  echo [V57] Sidebar navigation check failed.
  pause
  exit /b 1
)
echo [V57] Sidebar navigation check passed.
pause
