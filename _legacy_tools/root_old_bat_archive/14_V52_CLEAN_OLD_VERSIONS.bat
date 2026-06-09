@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo [v52] Report old Kakao Emoticon install folders and shortcuts.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\cleanup_old_versions_v52.ps1" -CurrentVersion 52 -Mode ReportOnly -ProtectSource "%~dp0"
pause
