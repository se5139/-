@echo off
setlocal
cd /d "%~dp0"
echo =====================================================
echo Kakao Emoticon v51 API guardrail ledger check
echo =====================================================
set "PY_CMD=python"
where py >nul 2>&1
if %errorlevel%==0 set "PY_CMD=py -3"
%PY_CMD% scripts\v51_api_guardrail_ledger_check.py
echo.
echo Check finished. Review outputs\v51_verification for details.
pause
