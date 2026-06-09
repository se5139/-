@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Kakao Emoticon v92 - Build Setup EXE

echo.
echo ============================================================
echo  Kakao Emoticon Profit System v92 - BUILD SETUP EXE
echo ============================================================
echo [v92] Creates installer\Output\KakaoEmoticonSetup_v92.exe when Inno Setup is installed.
echo [v92] This package keeps the beginner root folder compact and preserves the 5-flow UI.
echo [v92] Installer includes post-upgrade old-version backup-and-cleanup. No paid API is called.
echo.

set "PY_CMD="
where py >nul 2>nul
if not errorlevel 1 set "PY_CMD=py -3"
if "%PY_CMD%"=="" (
  where python >nul 2>nul
  if not errorlevel 1 set "PY_CMD=python"
)

if "%PY_CMD%"=="" (
  echo [ERROR] Python launcher was not found.
  echo Install Python 3.10+ and select Add Python to PATH, then run this again.
  pause
  exit /b 1
)

echo [v92] Python command: %PY_CMD%
%PY_CMD% scripts\build_inno_installer_v92.py --root "%CD%" --iss "%CD%\installer\KakaoEmoticonSetup_v92.iss"
set "ERR=%ERRORLEVEL%"
echo.
if "%ERR%"=="0" (
  echo [v92] Build completed.
  if exist "installer\Output\KakaoEmoticonSetup_v92.exe" explorer "%CD%\installer\Output"
) else (
  echo [v92] Build did not complete.
  echo [v92] Report file: %CD%\installer\v92_inno_build_report.json
  echo [v92] If Inno Setup is not installed, use the portable install BAT instead.
)
echo.
pause
exit /b %ERR%
