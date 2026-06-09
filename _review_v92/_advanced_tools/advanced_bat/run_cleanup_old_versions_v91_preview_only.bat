@echo off
cd /d "%~dp0\..\.."
set "PY_CMD=python"
where py >nul 2>nul && set "PY_CMD=py -3"
echo [v91] Installer post-step cleanup is preview-only. No files are deleted automatically.
%PY_CMD% scripts\cleanup_old_versions_v91.py --mode preview --current-version 91 --current-path "%CD%"
exit /b 0
