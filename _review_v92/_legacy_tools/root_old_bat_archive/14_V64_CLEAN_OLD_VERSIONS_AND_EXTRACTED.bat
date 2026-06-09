@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Kakao Emoticon v65 Clean Old Versions
echo [v65] Cleaning old versions safely...
python scripts\cleanup_old_versions_v65.py --yes --current-version 64
if errorlevel 1 (
 echo [v65] Cleanup failed.
 pause
 exit /b 1
)
echo [v65] Cleanup finished.
pause
exit /b 0
