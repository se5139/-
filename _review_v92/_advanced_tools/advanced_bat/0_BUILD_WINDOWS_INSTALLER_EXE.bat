@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Kakao Emoticon v86 - Build Setup EXE

echo.
echo ============================================================
echo  Kakao Emoticon Profit System v86 - BUILD SETUP EXE
echo ============================================================
echo [v86] This step creates installer\Output\KakaoEmoticonSetup_v86.exe.
echo [v86] Filename sanitizer hotfix: Windows-safe generated asset names, compact 5-flow UI retained.
echo [v86] No user data is deleted. No paid API is called.
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
  echo.
  pause
  exit /b 1
)

echo [v86] Python command: %PY_CMD%
echo [v86] Running build script now...
echo.
%PY_CMD% scripts\build_inno_installer_v86.py --root "%CD%" --iss "%CD%\installer\KakaoEmoticonSetup_v86.iss"
set "ERR=%ERRORLEVEL%"
echo.
if "%ERR%"=="0" (
  echo [v86] Build completed.
  if exist "installer\Output\KakaoEmoticonSetup_v86.exe" (
    echo [v86] Output: %CD%\installer\Output\KakaoEmoticonSetup_v86.exe
    explorer "%CD%\installer\Output"
  ) else (
    echo [WARN] Build script returned success, but output EXE was not found.
  )
) else (
  echo [v86] Build did not complete.
  echo [v86] Report file: %CD%\installer\v86_inno_build_report.json
  echo [v86] Alternative: run OPEN_V86_INNO_SCRIPT.bat and click Build / Compile in Inno Setup.
)
echo.
pause
exit /b %ERR%
