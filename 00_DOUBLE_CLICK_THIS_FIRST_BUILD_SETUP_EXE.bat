@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Kakao Emoticon v90 - Build Setup EXE

echo.
echo ============================================================
echo  Kakao Emoticon Profit System v90 - BUILD SETUP EXE
echo ============================================================
echo [v90] Creates installer\Output\KakaoEmoticonSetup_v90.exe when Inno Setup is installed.
echo [v90] This package keeps the beginner root folder compact and preserves the 5-flow UI.
echo [v90] Installer includes post-upgrade old-version backup-and-cleanup. No paid API is called.
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

echo [v90] Python command: %PY_CMD%
%PY_CMD% scripts\build_inno_installer_v90.py --root "%CD%" --iss "%CD%\installer\KakaoEmoticonSetup_v90.iss"
set "ERR=%ERRORLEVEL%"
echo.
if "%ERR%"=="0" (
  echo [v90] Build completed.
  if exist "installer\Output\KakaoEmoticonSetup_v90.exe" explorer "%CD%\installer\Output"
) else (
  echo [v90] Build did not complete.
  echo [v90] Report file: %CD%\installer\v90_inno_build_report.json
  echo [v90] If Inno Setup is not installed, use the portable install BAT instead.
)
echo.
pause
exit /b %ERR%
