@echo off
setlocal
cd /d "%~dp0"
python scripts\v73_final_user_approval_check.py
pause
