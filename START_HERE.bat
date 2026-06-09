@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title Kakao Emoticon v100 Start Here

echo.
echo ============================================================
echo  Kakao Emoticon Maker v100 Clean - Start Here
echo ============================================================
echo This is the recommended first button on a new PC.
echo.
echo Step 1/2: Verify package files.
echo.

call "%~dp0VERIFY_PACKAGE.bat"
if errorlevel 1 (
  echo.
  echo [STOP] Package verification failed.
  echo Please check the messages above before starting the app.
  pause
  exit /b 1
)

echo.
echo Step 2/2: Start the app.
echo.
call "%~dp0START_WINDOWS.bat"
exit /b %errorlevel%
