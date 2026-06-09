@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo [v63] Template engine manager check...
set "PYEXE="
if exist "%~dp0.venv\Scripts\python.exe" set "PYEXE=%~dp0.venv\Scripts\python.exe"
if not defined PYEXE set "PYEXE=python"
"%PYEXE%" "%~dp0scripts\v63_template_engine_manager_check.py"
if errorlevel 1 (
  echo [v63] Check failed. See kakao_emoticon_profit_system_v63_verification_report.json
  pause
  exit /b 1
)
echo [v63] Check passed.
pause
exit /b 0
