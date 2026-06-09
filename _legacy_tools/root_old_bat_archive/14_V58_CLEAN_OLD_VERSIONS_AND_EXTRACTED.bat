@echo off
setlocal
python scripts\cleanup_old_versions_v58.py
if errorlevel 1 pause
