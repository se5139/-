@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "APP_DIR=%~dp0"
set "PORT=8520"
set "PY_CMD="
where py >nul 2>nul
if not errorlevel 1 set "PY_CMD=py -3"
if "%PY_CMD%"=="" (
  where python >nul 2>nul
  if not errorlevel 1 set "PY_CMD=python"
)

title Kakao Emoticon v90 Launcher

echo.
echo ============================================================
echo  Kakao Emoticon Profit System v90 - First Run Launcher
echo ============================================================
echo [v90] APP_DIR=%APP_DIR%
echo [v90] PORT=%PORT%
echo [v90] This launcher prints every step so it should not look frozen.
echo.

if "%PY_CMD%"=="" (
  echo [ERROR] Python was not found.
  echo Install Python 3.10+ and check Add Python to PATH.
  pause
  exit /b 1
)

echo [v90] Python command: %PY_CMD%

if not exist "app.py" (
  echo [ERROR] app.py was not found.
  echo Please run this from the installed/extracted program folder.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [v90] Creating Python virtual environment...
  %PY_CMD% -m venv .venv
  if errorlevel 1 goto PYTHON_ERROR
)

if not exist ".venv\Scripts\activate.bat" (
  echo [ERROR] .venv activate script was not created.
  pause
  exit /b 1
)

call .venv\Scripts\activate.bat
python --version

if not exist ".venv\v90_ready.txt" (
  echo [v90] Installing required packages. First run may take several minutes.
  echo [v90] Step 1/2: upgrade pip
  python -m pip install --upgrade pip
  if errorlevel 1 goto PACKAGE_ERROR
  echo [v90] Step 2/2: install requirements.txt
  python -m pip install -r requirements.txt
  if errorlevel 1 goto PACKAGE_ERROR
  echo ready> .venv\v90_ready.txt
) else (
  echo [v90] Python environment already prepared.
)

echo [v90] Stopping existing Streamlit port %PORT% if needed...
python scripts\stop_port.py %PORT%

echo [v90] Starting Streamlit server window...
start "Kakao Emoticon v90 Server" cmd /k "cd /d ""%APP_DIR%"" && call .venv\Scripts\activate.bat && streamlit run app.py --server.address 127.0.0.1 --server.port %PORT% --server.fileWatcherType none --client.toolbarMode minimal"

echo [v90] Waiting for browser port...
python scripts\wait_for_port.py 127.0.0.1 %PORT% 90
if errorlevel 1 (
  echo [WARN] Port did not become ready within the wait time.
  echo [WARN] Check the server window for errors.
) else (
  echo [v90] Opening browser: http://127.0.0.1:%PORT%
  start "" http://127.0.0.1:%PORT%
)

echo.
echo [v90] App address: http://127.0.0.1:%PORT%
echo [v90] If browser does not open, copy the address above into Chrome or Edge.
echo.
pause
exit /b 0

:PYTHON_ERROR
echo [ERROR] Python virtual environment could not be created.
echo Check Python installation, antivirus, and folder permissions.
pause
exit /b 1

:PACKAGE_ERROR
echo [ERROR] Package installation failed.
echo Check internet connection and Python installation, then run 4_REPAIR_ENVIRONMENT.bat.
pause
exit /b 1
