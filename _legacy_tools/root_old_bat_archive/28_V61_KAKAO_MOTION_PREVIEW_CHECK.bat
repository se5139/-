@echo off
setlocal
cd /d "%~dp0"
echo [v61] Running Kakao motion preview verification...
set "PYEXE=python"
where py >nul 2>nul
if not errorlevel 1 set "PYEXE=py -3"
%PYEXE% "%~dp0scripts\v61_kakao_motion_preview_check.py"
pause
