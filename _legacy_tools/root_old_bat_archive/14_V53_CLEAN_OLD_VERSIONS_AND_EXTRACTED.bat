@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist "scripts\cleanup_old_versions_v53.ps1" (
  echo [ERROR] scripts\cleanup_old_versions_v53.ps1 was not found.
  pause
  exit /b 1
)
echo [v53] This will remove old Kakao Emoticon program folders and old desktop shortcuts only.
echo [v53] It will not delete Documents, Downloads, Pictures, or unrelated personal files.
echo [v53] User data inside old program folders will be backed up first.
echo.
set "DO_CLEAN=N"
set /p DO_CLEAN=Type Y to continue cleanup, Enter to cancel: 
if /I "%DO_CLEAN%"=="Y" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\cleanup_old_versions_v53.ps1" -CurrentVersion 53 -Mode AutoConfirm -ProtectSource "%~dp0" -ProtectTarget "%LOCALAPPDATA%\KakaoEmoticonProfitSystemV53"
) else (
  echo [v53] Cleanup cancelled.
)
echo.
pause
