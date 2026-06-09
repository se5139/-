@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo  Setup development environment
echo ============================================================
echo.

where py >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python launcher was not found.
  echo Install Python 3.10+ and check "Add Python to PATH".
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [INFO] Creating .venv...
  py -3 -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Failed to create .venv.
    pause
    exit /b 1
  )
)

echo [INFO] Upgrading pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
  echo [ERROR] pip upgrade failed.
  pause
  exit /b 1
)

echo [INFO] Installing runtime requirements...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo [ERROR] requirements install failed.
  pause
  exit /b 1
)

if exist "requirements-dev.txt" (
  echo [INFO] Installing developer requirements...
  ".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt
)

echo.
echo [OK] Development environment is ready.
echo Run: .\START_WINDOWS.bat
pause
