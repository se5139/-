@echo off
setlocal
cd /d "%~dp0"
python scripts\v57_installer_token_check.py
if errorlevel 1 (echo [V57] Installer token check failed.& pause& exit /b 1)
echo [V57] Installer token check passed.
pause
