@echo off
setlocal
cd /d "%~dp0"
python scripts\cleanup_old_versions_v84.py --yes --current-version 84
