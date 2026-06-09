@echo off
cd /d "%~dp0"
echo [v92] Running simple PNG/GIF output, filename, menu, upgrade cleanup, and diagnostic logging check...
set PY_CMD=python
where py >nul 2>nul && set PY_CMD=py -3
%PY_CMD% scripts\v92_error_diagnostics_output_check.py
echo.
echo [v92] Check finished. See v92_error_diagnostics_output_check_report.json
pause
