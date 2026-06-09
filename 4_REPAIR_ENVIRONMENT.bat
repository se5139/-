@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "PORT=8520"
set "PY_CMD="
where py >nul 2>nul
if not errorlevel 1 set "PY_CMD=py -3"
if "%PY_CMD%"=="" (
  where python >nul 2>nul
  if not errorlevel 1 set "PY_CMD=python"
)

title Kakao Emoticon v90 Repair

echo.
echo ============================================================
echo  Kakao Emoticon Profit System v90 - Repair Environment
echo ============================================================
echo.

if "%PY_CMD%"=="" (
  echo [ERROR] Python was not found.
  pause
  exit /b 1
)

echo [v90] Stopping old Streamlit port...
%PY_CMD% scripts\stop_port.py %PORT%

echo [v90] Rebuilding Python virtual environment...
if exist .venv rmdir /s /q .venv
%PY_CMD% -m venv .venv
if errorlevel 1 goto ERROR
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 goto ERROR
python -m pip install -r requirements.txt
if errorlevel 1 goto ERROR
echo ready> .venv\v90_ready.txt

echo [v90] Running diagnostics...
python scripts\diagnose_environment.py
if exist outputs\installer_diagnostics\installation_diagnostic_report.html start "" outputs\installer_diagnostics\installation_diagnostic_report.html

echo.
echo [v90] Repair completed. Run 00_STEP_3_START_PROGRAM.bat.
pause
exit /b 0

:ERROR
echo [ERROR] Repair failed.
echo Check Python 3.10+, internet connection, antivirus block, and folder permissions.
pause
exit /b 1
