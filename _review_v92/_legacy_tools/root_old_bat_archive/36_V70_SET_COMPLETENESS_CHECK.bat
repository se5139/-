@echo off
setlocal
cd /d "%~dp0"
python scripts\v70_set_completeness_check.py
pause
