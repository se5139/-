@echo off
setlocal
cd /d "%~dp0"
python scripts\cleanup_old_versions_v80.py --yes --current-version 80
pause
