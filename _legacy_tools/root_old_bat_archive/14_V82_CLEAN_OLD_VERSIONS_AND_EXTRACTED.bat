@echo off
setlocal
cd /d "%~dp0"
python scripts\cleanup_old_versions_v82.py --yes --current-version 82
pause
