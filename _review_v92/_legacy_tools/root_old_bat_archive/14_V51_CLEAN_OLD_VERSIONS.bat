@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\cleanup_old_versions_v51.ps1" -CurrentVersion 51 -Mode ReportOnly -ProtectSource "%~dp0"
pause
