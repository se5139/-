@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Kakao Emoticon v81 Installer Builder

echo.
echo ============================================================
echo  Kakao Emoticon Profit System v81 - Installer Builder
echo ============================================================
echo [v81] This window should show progress immediately.
echo [v81] If Windows shows a publisher warning, choose Run only if this is the ZIP you downloaded from ChatGPT.
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
  echo Install Python 3.10+ and check "Add Python to PATH", then run this again.
  echo.
  pause
  exit /b 1
)

echo [v81] Python command: %PY_CMD%
echo [v81] Starting build script...
echo.

%PY_CMD% scripts\build_inno_installer_v81.py --root "%CD%" --iss "%CD%\installer\KakaoEmoticonSetup_v81.iss"
set "ERR=%ERRORLEVEL%"

echo.
if "%ERR%"=="0" (
  echo [v81] Build completed.
  if exist "installer\Output\KakaoEmoticonSetup_v81.exe" (
    echo [v81] Output: %CD%\installer\Output\KakaoEmoticonSetup_v81.exe
    explorer "%CD%\installer\Output"
  )
) else (
  echo [v81] Build did not complete.
  echo [v81] Report file: %CD%\installer\v81_inno_build_report.json
  echo [v81] Alternative: run OPEN_V81_INNO_SCRIPT.bat and click Build/Compile in Inno Setup.
)
echo.
pause
exit /b %ERR%
