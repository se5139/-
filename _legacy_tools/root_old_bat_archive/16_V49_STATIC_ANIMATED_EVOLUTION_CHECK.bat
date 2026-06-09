@echo off
setlocal
cd /d "%~dp0"
echo =====================================================
echo Kakao Emoticon v49 static/animated evolution check
echo =====================================================
set "PY_CMD=python"
where py >nul 2>&1
if %errorlevel%==0 set "PY_CMD=py -3"
%PY_CMD% scripts\v49_static_animated_evolution_check.py
echo.
echo Check finished. Review outputs\v49_verification for details.
pause
