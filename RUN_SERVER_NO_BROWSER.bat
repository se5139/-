@echo off
setlocal
cd /d "%~dp0"
set "KAKAO_NO_BROWSER=1"
set "CODEX_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" app.py
    goto :end
)

if exist "%CODEX_PY%" (
    "%CODEX_PY%" app.py
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

echo Python was not found.
pause

:end
endlocal
