@echo off
cd /d "%~dp0"
python scripts\cleanup_old_versions_v67.py --yes --current-version 67
pause
