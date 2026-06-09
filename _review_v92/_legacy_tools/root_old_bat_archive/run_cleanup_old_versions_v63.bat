@echo off
setlocal
cd /d "%~dp0"
echo [v63] Safe cleanup is starting.
echo [v63] Old extracted/install folders v1-v61 will be removed only if their names match Kakao version patterns.
echo [v63] User data folders are backed up before removal.
echo.
set "PYEXE="
if exist "%~dp0.venv\Scripts\python.exe" set "PYEXE=%~dp0.venv\Scripts\python.exe"
if not defined PYEXE set "PYEXE=python"
"%PYEXE%" "%~dp0scripts\cleanup_old_versions_v63.py" --yes --current-version 63 --protect "%~dp0"
if errorlevel 1 (
  echo.
  echo [v63] Cleanup finished with warnings/errors. Check the report path printed above.
  pause
) else (
  echo.
  echo [v63] Cleanup finished.
)
