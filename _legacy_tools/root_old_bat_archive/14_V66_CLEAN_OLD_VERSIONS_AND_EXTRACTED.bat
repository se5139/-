@echo off
cd /d "%~dp0"
python scripts\cleanup_old_versions_v66.py --yes --current-version 66
pause
