@echo off
setlocal
cd /d "%~dp0"

echo.
echo Kakao Emoticon Maker v100 Clean
echo --------------------------------
echo Starting local app...
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" app.py
    goto :end
)

where python >nul 2>nul
if %errorlevel%==0 (
    python app.py
    goto :end
)

where py >nul 2>nul
if %errorlevel%==0 (
    py app.py
    goto :end
)

set "CODEX_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%CODEX_PY%" (
    "%CODEX_PY%" app.py
    goto :end
)

echo Python was not found on PATH.
echo Install Python 3.10 or newer, create a .venv in this folder,
echo or run this project again from Codex where bundled Python is available.
echo.
pause

:end
endlocal
