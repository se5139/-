@echo off
cd /d "%~dp0"
py -3 "%CD%\scripts\v56_inno_compiler_detector_check.py"
if errorlevel 1 python "%CD%\scripts\v56_inno_compiler_detector_check.py"
pause
