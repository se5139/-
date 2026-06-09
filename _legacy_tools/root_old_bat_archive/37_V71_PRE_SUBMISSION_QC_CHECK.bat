@echo off
setlocal
cd /d "%~dp0"
python scripts\v71_pre_submission_qc_check.py
pause
