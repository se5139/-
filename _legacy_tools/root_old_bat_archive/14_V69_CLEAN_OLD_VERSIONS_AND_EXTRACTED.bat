@echo off
setlocal
cd /d "%~dp0"
if exist "scripts\cleanup_old_versions_v68.py" (
  python scripts\cleanup_old_versions_v68.py --yes --current-version 69
) else (
  echo Cleanup helper not found. Use Windows Apps settings or delete old extracted kakao_emoticon_profit_system_vXX folders manually after backup.
)
pause
