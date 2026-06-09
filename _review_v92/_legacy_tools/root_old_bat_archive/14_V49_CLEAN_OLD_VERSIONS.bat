@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo [v49] Old-version cleanup tool.
echo [v49] It removes old install folders and old desktop shortcuts only.
echo [v49] User data is backed up before cleanup.
set "CLEAN_OLD=N"
set /p CLEAN_OLD=Type Y to clean old versions, Enter to cancel: 
if /I "%CLEAN_OLD%"=="Y" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\cleanup_old_versions_v49.ps1" -CurrentVersion 49 -Mode AutoConfirm -ProtectSource "%~dp0" -ProtectTarget "%~dp0"
) else (
  echo [v49] Canceled. No files deleted.
)
pause
