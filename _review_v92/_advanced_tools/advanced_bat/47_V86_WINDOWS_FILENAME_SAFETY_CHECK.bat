@echo off
cd /d "%~dp0"
echo [v86] Checking Windows-safe generated filenames...
set PY_CMD=python
where py >nul 2>nul && set PY_CMD=py -3
%PY_CMD% scripts\v86_windows_filename_safety_check.py
echo.
echo [v86] Check finished.
pause
