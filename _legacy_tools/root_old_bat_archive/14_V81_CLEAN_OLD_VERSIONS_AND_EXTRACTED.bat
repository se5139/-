@echo off
setlocal
cd /d "%~dp0"
python scripts\cleanup_old_versions_v81.py --yes --current-version 81
pause
