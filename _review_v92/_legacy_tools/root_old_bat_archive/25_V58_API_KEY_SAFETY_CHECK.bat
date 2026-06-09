@echo off
setlocal
python scripts\v58_api_key_safety_check.py
if errorlevel 1 pause
