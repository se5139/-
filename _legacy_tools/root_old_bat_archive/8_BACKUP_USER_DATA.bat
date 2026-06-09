@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo [v48] Backing up user data...
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe scripts\backup_user_data.py
) else (
  py -3 scripts\backup_user_data.py
)
pause
