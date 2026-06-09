@echo off
cd /d "%~dp0"
echo [v91] Running simple PNG/GIF output, filename, menu, and upgrade cleanup check...
set PY_CMD=python
where py >nul 2>nul && set PY_CMD=py -3
%PY_CMD% scripts\v91_simple_png_gif_output_check.py
echo.
echo [v91] Check finished. See v91_simple_png_gif_output_check_report.json
pause
