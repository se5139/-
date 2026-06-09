@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe scripts\v76_rejection_to_regeneration_check.py
) else (
  python scripts\v76_rejection_to_regeneration_check.py
)
pause
