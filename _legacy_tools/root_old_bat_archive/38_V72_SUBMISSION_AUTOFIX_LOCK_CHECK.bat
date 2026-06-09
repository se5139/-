@echo off
setlocal
cd /d "%~dp0"
python scripts\v72_submission_autofix_lock_check.py
pause
