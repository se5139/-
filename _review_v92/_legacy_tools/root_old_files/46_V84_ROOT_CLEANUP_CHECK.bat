@echo off
setlocal
cd /d "%~dp0"
python scripts\v84_root_runtime_check.py
pause
