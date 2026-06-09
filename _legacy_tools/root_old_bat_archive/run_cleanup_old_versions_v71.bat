@echo off
setlocal
cd /d "%~dp0"
python scripts\cleanup_old_versions_v69.py --yes --current-version 71
