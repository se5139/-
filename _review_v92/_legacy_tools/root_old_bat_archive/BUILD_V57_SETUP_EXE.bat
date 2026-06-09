@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo [v57] Building Windows installer EXE with Inno Setup...
echo [v57] This script searches PATH, Program Files, LocalAppData, and Inno shortcut targets.
echo.

set "PYEXE="
where py >nul 2>nul
if not errorlevel 1 set "PYEXE=py -3"
if "%PYEXE%"=="" (
  where python >nul 2>nul
  if not errorlevel 1 set "PYEXE=python"
)
if "%PYEXE%"=="" (
  echo [ERROR] Python was not found. Run 1_INSTALL_NOW.bat or install Python first.
  pause
  exit /b 1
)

%PYEXE% "%CD%\scripts\build_inno_installer_v57.py" --root "%CD%" --iss "%CD%\installer\KakaoEmoticonSetup_v57.iss"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo [ERROR] v57 installer build did not complete. exit=%RC%
  echo Check: installer\v57_inno_build_report.json
  echo Alternative: run OPEN_V57_INNO_SCRIPT.bat, then click Build or Compile in Inno Setup.
  pause
  exit /b %RC%
)

echo.
echo [v57] Build completed.
echo Output: %CD%\installer\Output\KakaoEmoticonSetup_v57.exe
pause
exit /b 0
