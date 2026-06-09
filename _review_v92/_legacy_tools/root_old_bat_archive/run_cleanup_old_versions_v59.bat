@echo off
setlocal
cd /d "%~dp0"
echo [v59] Safe cleanup is starting.
echo [v59] Old extracted/install folders v1-v58 will be removed only if their names match Kakao version patterns.
echo [v59] User data folders are backed up before removal.
echo.
set "PYEXE="
if exist "%~dp0.venv\Scripts\python.exe" set "PYEXE=%~dp0.venv\Scripts\python.exe"
if not defined PYEXE set "PYEXE=python"
"%PYEXE%" "scripts\cleanup_old_versions_v59.py" --yes --current-version 59 --protect "%~dp0"
if errorlevel 1 (
  echo.
  echo [v59] Cleanup finished with warnings/errors. Check the report path printed above.
  pause
) else (
  echo.
  echo [v59] Cleanup finished.
)
