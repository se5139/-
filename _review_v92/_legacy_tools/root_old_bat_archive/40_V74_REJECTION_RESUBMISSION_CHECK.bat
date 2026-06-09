@echo off
setlocal
cd /d "%~dp0"
python scripts\v74_rejection_resubmission_check.py
pause
