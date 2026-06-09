@echo off
setlocal
cd /d "%~dp0"
python scripts\v75_capture_rejection_check.py
pause
