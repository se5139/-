@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo [v65] Running safe cleanup...
python scripts\cleanup_old_versions_v65.py --yes --current-version 64
exit /b %errorlevel%
