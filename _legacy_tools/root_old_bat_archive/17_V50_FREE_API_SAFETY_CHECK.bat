@echo off
setlocal
cd /d "%~dp0"
echo =====================================================
echo Kakao Emoticon v50 free API safety mode check
echo =====================================================
set "PY_CMD=python"
where py >nul 2>&1
if %errorlevel%==0 set "PY_CMD=py -3"
%PY_CMD% scripts50_free_api_safety_check.py
echo.
echo Check finished. Review outputs50_verification for details.
pause
