@echo off
cd /d "%~dp0"
python scripts\cleanup_old_versions_v68.py --yes --current-version 68
exit /b %ERRORLEVEL%
