@echo off
setlocal
cd /d "%~dp0"
echo [v61] Safe cleanup is starting.
echo [v61] Old extracted/install folders v1-v60 will be removed only if their names match Kakao version patterns.
echo [v61] User data folders are backed up before removal.
echo.
set "PYEXE="
if exist "%~dp0.venv\Scripts\python.exe" set "PYEXE=%~dp0.venv\Scripts\python.exe"
if not defined PYEXE set "PYEXE=python"
"%PYEXE%" "%~dp0scripts\cleanup_old_versions_v61.py" --yes --current-version 61 --protect "%~dp0"
if errorlevel 1 (
  echo.
  echo [v61] Cleanup finished with warnings/errors. Check the report path printed above.
  pause
) else (
  echo.
  echo [v61] Cleanup finished.
)
