@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "PY_CMD=python"
where py >nul 2>nul
if not errorlevel 1 set "PY_CMD=py -3"
echo [v52] Running static-to-animated apply check...
%PY_CMD% scripts\v52_static_to_animated_apply_check.py
pause
