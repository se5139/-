@echo off
setlocal
cd /d "%~dp0"
python scripts\cleanup_old_versions_v72.py --yes --current-version 74
exit /b %ERRORLEVEL%
