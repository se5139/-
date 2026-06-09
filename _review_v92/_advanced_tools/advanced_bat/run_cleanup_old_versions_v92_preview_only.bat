@echo off
cd /d "%~dp0\..\.."
set "PY_CMD=python"
where py >nul 2>nul && set "PY_CMD=py -3"
echo [v92] Installer post-step cleanup is preview-only. No files are deleted automatically.
%PY_CMD% scripts\cleanup_old_versions_v92.py --mode preview --current-version 92 --current-path "%CD%"
exit /b 0
