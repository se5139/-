@echo off
cd /d "%~dp0"
set "PYEXE=python"
where py >nul 2>nul
if not errorlevel 1 set "PYEXE=py -3"
%PYEXE% "%~dp0scripts\v67_video_quality_direction_check.py"
pause
