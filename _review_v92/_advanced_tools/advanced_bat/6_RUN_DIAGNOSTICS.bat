@echo off
setlocal
cd /d "%~dp0"
set "PY_CMD="
where py >nul 2>nul
if not errorlevel 1 set "PY_CMD=py -3"
if "%PY_CMD%"=="" (where python >nul 2>nul && set "PY_CMD=python")
if "%PY_CMD%"=="" (echo [ERROR] Python not found.& pause& exit /b 1)
if exist .venv\Scripts\python.exe (call .venv\Scripts\activate.bat)
python scripts\diagnose_environment.py
if exist outputs\installer_diagnostics\installation_diagnostic_report.html start "" outputs\installer_diagnostics\installation_diagnostic_report.html
pause
