@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."
set "PY_CMD="
where py >nul 2>nul
if not errorlevel 1 set "PY_CMD=py -3"
if "%PY_CMD%"=="" (
  where python >nul 2>nul
  if not errorlevel 1 set "PY_CMD=python"
)
if "%PY_CMD%"=="" (
  echo [v90][WARN] Python was not found. Old-version cleanup skipped.
  exit /b 0
)
echo [v90] Post-upgrade cleanup: backing up likely user data, then removing old v89-and-lower folders.
%PY_CMD% scripts\cleanup_old_versions_v90.py --mode delete --yes --confirm DELETE_OLD_KAKAO_VERSIONS --current-version 90 --current-path "%CD%"
if errorlevel 1 (
  echo [v90][WARN] Post-upgrade cleanup did not complete. Run 00_STEP_4_SAFE_CLEAN_OLD_VERSIONS.bat later.
  exit /b 0
)
exit /b 0
