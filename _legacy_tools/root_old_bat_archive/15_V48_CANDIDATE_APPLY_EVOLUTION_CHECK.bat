@echo off
setlocal
cd /d "%~dp0"
echo ================================================
echo Kakao Emoticon v48 candidate apply/evolution check
echo ================================================
set "PY_CMD=python"
where py >nul 2>&1
if %errorlevel%==0 set "PY_CMD=py -3"
%PY_CMD% scripts\v48_candidate_apply_evolution_check.py
echo.
echo Check finished. Review outputs\v48_verification for details.
pause
