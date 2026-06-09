@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo [v48] Running data safety check...
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe scripts\data_safety_check.py
) else (
  py -3 scripts\data_safety_check.py
)
pause
