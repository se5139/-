@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
set "SRC=%CD%"
set "APP_NAME=KakaoEmoticonProfitSystemV90"
set "TARGET=%LOCALAPPDATA%\%APP_NAME%"
set "LOG_DIR=%LOCALAPPDATA%\%APP_NAME%_install_logs"
set "LOG_FILE=%LOG_DIR%\install_copy_log.txt"

title Kakao Emoticon v90 Portable Installer

echo.
echo ============================================================
echo  Kakao Emoticon Profit System v90 - Portable Installer
echo ============================================================
echo [v90] Source: %SRC%
echo [v90] Target: %TARGET%
echo [v90] This fallback installer copies files, prepares Python, and creates shortcuts.
echo [v90] After successful upgrade, old version folders are backed up and cleaned automatically.
echo.

if not exist "%SRC%\app.py" (
  echo [ERROR] app.py was not found.
  echo Please extract the ZIP completely first.
  pause
  exit /b 1
)

set "PY_CMD="
where py >nul 2>nul
if not errorlevel 1 set "PY_CMD=py -3"
if "%PY_CMD%"=="" (
  where python >nul 2>nul
  if not errorlevel 1 set "PY_CMD=python"
)
if "%PY_CMD%"=="" (
  echo [ERROR] Python was not found.
  echo Install Python 3.10+ and select Add Python to PATH.
  pause
  exit /b 1
)

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
if not exist "%TARGET%" mkdir "%TARGET%"

echo [v90] Copying program files...
robocopy "%SRC%" "%TARGET%" /E /R:2 /W:1 /XD .venv __pycache__ outputs installer /XF *.zip *.sha256.txt > "%LOG_FILE%"
set "RC=%ERRORLEVEL%"
if %RC% GEQ 8 goto COPY_ERROR

echo [v90] Copy completed. robocopy code=%RC%
echo [v90] Creating shortcuts...
%PY_CMD% "%TARGET%\scripts\create_shortcuts_v90.py" "%TARGET%"
if errorlevel 1 echo [WARN] Shortcut creation failed. Program files are still installed.

echo.
echo [v90] Preparing Python environment...
call "%TARGET%\4_REPAIR_ENVIRONMENT.bat"
if errorlevel 1 goto ENV_WARN

echo.
echo [v90] Install completed.
echo [v90] Install folder: %TARGET%
echo.
echo [v90] Upgrade cleanup is enabled.
echo [v90] Old v89-and-lower Kakao Emoticon folders will be backed up, then removed.
echo [v90] Current v90 folder and newer folders are excluded.
%PY_CMD% "%TARGET%\scripts\cleanup_old_versions_v90.py" --mode delete --yes --confirm DELETE_OLD_KAKAO_VERSIONS --current-version 90 --current-path "%TARGET%"
if errorlevel 1 echo [WARN] Upgrade cleanup did not complete. You can run 00_STEP_4_SAFE_CLEAN_OLD_VERSIONS.bat later.
echo.
echo [v90] Run 00_STEP_3_START_PROGRAM.bat or the desktop shortcut.
pause
exit /b 0

:ENV_WARN
echo.
echo [WARN] Files were copied, but Python environment setup did not finish.
echo Run 4_REPAIR_ENVIRONMENT.bat, then run 00_STEP_3_START_PROGRAM.bat.
pause
exit /b 0

:COPY_ERROR
echo [ERROR] File copy failed. robocopy code=%RC%
echo [ERROR] Log file: %LOG_FILE%
echo.
echo Recommended fix:
echo 1. Move this folder to C:\KakaoEmoticonV90.
echo 2. Run 00_STEP_2_PORTABLE_INSTALL_NOW.bat again.
echo 3. Or build/run the Inno Setup installer.
pause
exit /b 1
