@echo off
setlocal
cd /d "%~dp0"
echo [v60] Safe cleanup is starting.
echo [v60] Old extracted/install folders v1-v59 will be removed only if their names match Kakao version patterns.
echo [v60] User data folders are backed up before removal.
echo.
set "PYEXE="
if exist "%~dp0.venv\Scripts\python.exe" set "PYEXE=%~dp0.venv\Scripts\python.exe"
if not defined PYEXE set "PYEXE=python"
"%PYEXE%" "%~dp0scripts\cleanup_old_versions_v60.py" --yes --current-version 60 --protect "%~dp0"
if errorlevel 1 (
  echo.
  echo [v60] Cleanup finished with warnings/errors. Check the report path printed above.
  pause
) else (
  echo.
  echo [v60] Cleanup finished.
)
